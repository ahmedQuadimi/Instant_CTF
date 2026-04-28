import math
from collections import defaultdict

from django.core.cache import cache
from django.db.models import Count, Min
from django.utils import timezone

from Challenges.models import Challenge
from Events.models import EventRoster
from Scoring.models import Solve
from Scoring.utils import calculate_event_points

SCOREBOARD_CACHE_TIMEOUT = 300


def get_event_scoreboard_cache_key(event_id):
    return f"event_scoreboard:{event_id}"


def invalidate_event_scoreboard_cache(event_id):
    cache.delete(get_event_scoreboard_cache_key(event_id))




def _compute_ranked_teams(event):
    roster_rows = list(
        EventRoster.objects.filter(event=event)
        .values("team_id", "team__name")
        .annotate(joined_at=Min("joined_at"))
    )

    teams_by_id = {
        row["team_id"]: {
            "team_name": row["team__name"],
            "score": 0,
            "solve_count": 0,
            "last_solve_at": None,
            "joined_at": row["joined_at"],
        }
        for row in roster_rows
    }

    # Get scoring parameters from the event model
    scoring_strategy = getattr(event, "scoring_strategy", "STANDARD")
    base_points = getattr(event, "max_points", 500)
    min_points = getattr(event, "min_points", 50)
    decay_factor = getattr(event, "decay_factor", 0.08)

    # Count total solves per challenge (for dynamic recomputation)
    challenge_solve_counts = {}
    if scoring_strategy in ("EXPONENTIAL", "LINEAR"):
        challenge_solve_counts = dict(
            Solve.objects.filter(challenge__event=event)
            .values_list("challenge_id")
            .annotate(total=Count("id"))
            .values_list("challenge_id", "total")
        )

    solves_by_team = defaultdict(list)
    for solve in (
        Solve.objects.filter(team_id__in=teams_by_id, challenge__event=event)
        .select_related("challenge")
        .order_by("timestamp")
    ):
        solves_by_team[solve.team_id].append(solve)

    ranked_teams = []
    for team_id, team_data in teams_by_id.items():
        solves = solves_by_team.get(team_id, [])

        if solves:
            total_score = 0
            for solve in solves:
                if scoring_strategy in ("EXPONENTIAL", "LINEAR"):
                    sc = challenge_solve_counts.get(solve.challenge_id, 1)
                    total_score += calculate_event_points(
                        scoring_strategy, base_points, min_points, decay_factor, sc
                    )
                else:
                    total_score += solve.awarded_points

            team_data["score"] = total_score
            team_data["solve_count"] = len(solves)
            team_data["last_solve_at"] = solves[-1].timestamp

        ranked_teams.append(
            {
                "team_name": team_data["team_name"],
                "score": team_data["score"],
                "solve_count": team_data["solve_count"],
                "last_solve_at": team_data["last_solve_at"],
                "joined_at": team_data["joined_at"],
            }
        )

    ranked_teams.sort(
        key=lambda team: (
            -team["score"],
            team["last_solve_at"] is None,
            team["last_solve_at"] or team["joined_at"],
        )
    )

    for rank, team in enumerate(ranked_teams, start=1):
        team["rank"] = rank

    return ranked_teams


def get_cached_ranked_teams(event):
    cache_key = get_event_scoreboard_cache_key(event.id)
    ranked_teams = cache.get(cache_key)
    if ranked_teams is None:
        ranked_teams = _compute_ranked_teams(event)
        cache.set(cache_key, ranked_teams, SCOREBOARD_CACHE_TIMEOUT)
    return ranked_teams


def build_event_scoreboard(event):
    return {
        "ranked_teams": get_cached_ranked_teams(event),
        "event_ended": event.end_time < timezone.now(),
    }
