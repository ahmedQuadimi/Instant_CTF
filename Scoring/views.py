from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from Events.utils import get_event_or_404
from Scoring.services import build_event_scoreboard


@require_GET
@login_required
@never_cache
def event_scoreboard(request, event_id):
    event = get_event_or_404(event_id)
    scoreboard = build_event_scoreboard(event)

    return render(
        request,
        "scoring/event_scoreboard.html",
        {
            "ranked_teams": scoreboard["ranked_teams"],
            "event": event,
            "event_ended": scoreboard["event_ended"],
        },
    )


@require_GET
@login_required
@never_cache
def event_scoreboard_data(request, event_id):
    event = get_event_or_404(event_id)
    scoreboard = build_event_scoreboard(event)

    return JsonResponse(
        {
            "event_ended": scoreboard["event_ended"],
            "ranked_teams": [
                {
                    "rank": team["rank"],
                    "team_name": team["team_name"],
                    "score": team["score"],
                    "solve_count": team["solve_count"],
                    "last_solve_at": (
                        team["last_solve_at"].isoformat()
                        if team["last_solve_at"] is not None
                        else None
                    ),
                }
                for team in scoreboard["ranked_teams"]
            ],
        }
    )
