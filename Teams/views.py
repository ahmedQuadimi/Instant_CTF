from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from Events.models import EventRoster
from Events.utils import get_event_or_404
from .models import Team

# Create your views here.


def event_teams(request, event_id):
    event = get_event_or_404(event_id)
    teams = (
        Team.objects.filter(event_rosters__event=event)
        .annotate(
            member_count=Count(
                "event_rosters",
                filter=Q(event_rosters__event=event),
                distinct=True,
            )
        )
        .distinct()
    )
    return render(request, "teams/event_teams.html", {"event": event, "teams": teams})


def teams(request):
    # TODO: implements the page for the teams list
    pass


def team_details(request, team_id, event_id=None):
    team = get_object_or_404(Team, pk=team_id)
    event = get_event_or_404(event_id) if event_id is not None else None

    if event is None:
        return render(
            request,
            "teams/team_details.html",
            {
                "event": event,
                "team": team,
                "members": [],
                "solves": [],
            },
        )

    is_team_in_event = EventRoster.objects.filter(event=event, team=team).exists()
    if not is_team_in_event:
        raise Http404("Team is not participating in this event.")

    members = EventRoster.objects.filter(event=event, team=team).select_related("user")
    solves = []  # TODO: populate from Scoring app once available

    return render(
        request,
        "teams/team_details.html",
        {
            "event": event,
            "team": team,
            "members": members,
            "solves": solves,
        },
    )


def request_join(request, team_id):
    # TODO: implements the POST request to join a specific team
    pass


def manage(request, team_id):
    # TODO: implements the page where we manage the specific team
    pass


def create(request):
    # TODO: implements the page where we create a new team
    pass
