from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError

from Events.models import EventRoster
from Events.utils import get_event_or_404
from .models import Team
from .models import TeamJoinRequest


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
    team_rows = Team.objects.select_related("captain").annotate(
        member_count=Count("event_rosters", distinct=True)
    ).order_by("name")
    return render(request, "teams/teams.html", {"teams": team_rows})


def team_details(request, team_id, event_id=None):
    team = get_object_or_404(Team, pk=team_id)
    event = get_event_or_404(event_id) if event_id is not None else None

    if event is None:
        return render(
            request,
            "teams/team_detail.html",
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
        "teams/team_detail.html",
        {
            "event": event,
            "team": team,
            "members": members,
            "solves": solves,
        },
    )


@login_required
def request_join(request, team_id):
    team = get_object_or_404(Team, pk=team_id)

    if request.method == "POST":
        try:
            TeamJoinRequest.objects.create(user=request.user, team=team, status="PENDING")
            messages.success(request, "Join request submitted.")
        except IntegrityError:
            messages.info(request, "You already have a pending request for this team.")
        return redirect("team_detail", team_id=team.id)

    return render(request, "teams/request_join.html", {"team": team})


@login_required
def manage(request, team_id):
    team = get_object_or_404(Team, pk=team_id)
    if team.captain_id != request.user.id:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    # Handle accept / reject POST actions
    if request.method == "POST":
        action = request.POST.get("action", "")
        join_request_id = request.POST.get("join_request_id", "")

        if action in ("accept", "reject") and join_request_id:
            try:
                join_request = TeamJoinRequest.objects.get(
                    pk=int(join_request_id),
                    team=team,
                    status="PENDING",
                )
            except (TeamJoinRequest.DoesNotExist, ValueError):
                messages.error(request, "Join request not found.")
            else:
                if action == "accept":
                    join_request.status = "APPROVED"
                    join_request.save(update_fields=["status"])
                    messages.success(
                        request,
                        f"{join_request.user.username} has been accepted to the team.",
                    )
                elif action == "reject":
                    join_request.status = "REJECTED"
                    join_request.save(update_fields=["status"])
                    messages.info(
                        request,
                        f"{join_request.user.username}'s request has been rejected.",
                    )

        return redirect("team_manage", team_id=team.id)

    # GET: load members and pending requests
    members = EventRoster.objects.filter(team=team).select_related("user", "event")
    pending_requests = TeamJoinRequest.objects.filter(
        team=team, status="PENDING"
    ).select_related("user")

    return render(
        request,
        "teams/team_manage.html",
        {
            "team": team,
            "members": members,
            "pending_requests": pending_requests,
        },
    )


@login_required
def create(request):
    errors = []

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        is_public = request.POST.get("is_public") == "on"

        if not name:
            errors.append("Team name is required.")

        if not errors:
            try:
                team = Team.objects.create(name=name, is_public=is_public, captain=request.user)
                messages.success(request, f'Team "{team.name}" created successfully.')
                return redirect("team_detail", team_id=team.id)
            except IntegrityError:
                errors.append("A team with this name already exists.")

    return render(request, "teams/team_create.html", {"errors": errors})
