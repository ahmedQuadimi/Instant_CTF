from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.db.models import Min
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import cache_page

from Events.models import EventRoster
from Events.utils import get_event_or_404
from Scoring.models import Solve
from Scoring.utils import calculate_event_points


@login_required
@cache_page(30)
def event_scoreboard(request, event_id):
    event = get_event_or_404(event_id)
    event_ended = event.end_time < timezone.now()

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
            team_data["score"] = sum(
                calculate_event_points(
                    event.scoring_strategy,
                    event.base_points,
                    event.minimum_points,
                    event.decay_parameter,
                    solve.challenge.solves_count,
                )
                for solve in solves
            )
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

    return render(
        request,
        "scoring/event_scoreboard.html",
        {
            "ranked_teams": ranked_teams,
            "event": event,
            "event_ended": event_ended,
        },
    )
