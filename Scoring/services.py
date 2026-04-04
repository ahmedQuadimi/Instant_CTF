from collections import defaultdict

from django.core.cache import cache
from django.db.models import Min
from django.utils import timezone

from Events.models import EventRoster
from Scoring.models import Solve

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
            team_data["score"] = sum(solve.awarded_points for solve in solves)
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
