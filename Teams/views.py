from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError

from Events.models import EventRoster
from Events.utils import get_event_or_404
from .models import Team, TeamJoinRequest, TeamMembership


def event_teams(request, event_id):
    event = get_event_or_404(event_id)
    teams = (
        Team.objects.filter(event_rosters__event=event)
        .annotate(
            member_count=Count(
                "teammembership",
                distinct=True,
            )
        )
        .distinct()
    )
    return render(request, "teams/event_teams.html", {"event": event, "teams": teams})


def teams(request):
    query = request.GET.get("q", "").strip()
    public_filter = request.GET.get("public", "")

    team_rows = Team.objects.select_related("captain").annotate(
        member_count=Count("teammembership", distinct=True)
    )

    if query:
        team_rows = team_rows.filter(name__icontains=query)

    if public_filter == "public":
        team_rows = team_rows.filter(is_public=True)
    elif public_filter == "private":
        team_rows = team_rows.filter(is_public=False)

    team_rows = team_rows.order_by("-global_rating")

    return render(
        request,
        "teams/teams.html",
        {
            "teams": team_rows,
            "query": query,
            "public_filter": public_filter,
        },
    )


def team_details(request, team_id, event_id=None):
    team = get_object_or_404(Team, pk=team_id)
    event = get_event_or_404(event_id) if event_id is not None else None

    is_member = False
    is_captain = False
    has_pending_request = False
    if request.user.is_authenticated:
        is_captain = (team.captain == request.user)
        is_member = TeamMembership.objects.filter(team=team, user=request.user).exists()
        has_pending_request = TeamJoinRequest.objects.filter(team=team, user=request.user, status="PENDING").exists()

    if event is None:
        memberships = TeamMembership.objects.filter(team=team).select_related("user")
        return render(
            request,
            "teams/team_detail.html",
            {
                "event": event,
                "team": team,
                "memberships": memberships,
                "solves": [],
                "is_captain": is_captain,
                "is_member": is_member,
                "has_pending_request": has_pending_request,
            },
        )

    is_team_in_event = EventRoster.objects.filter(event=event, team=team).exists()
    if not is_team_in_event:
        raise Http404("Team is not participating in this event.")

    memberships = TeamMembership.objects.filter(team=team).select_related("user")
    solves = []  # TODO: populate from Scoring app once available

    is_member = False
    is_captain = False
    has_pending_request = False
    if request.user.is_authenticated:
        is_captain = (team.captain == request.user)
        is_member = TeamMembership.objects.filter(team=team, user=request.user).exists()
        has_pending_request = TeamJoinRequest.objects.filter(team=team, user=request.user, status="PENDING").exists()

    return render(
        request,
        "teams/team_detail.html",
        {
            "event": event,
            "team": team,
            "memberships": memberships,
            "solves": solves,
            "is_captain": is_captain,
            "is_member": is_member,
            "has_pending_request": has_pending_request,
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
                    join_request.status = "ACCEPTED"
                    join_request.save(update_fields=["status"])
                    TeamMembership.objects.get_or_create(team=team, user=join_request.user)
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
    memberships = TeamMembership.objects.filter(team=team).select_related("user")
    pending_requests = TeamJoinRequest.objects.filter(
        team=team, status="PENDING"
    ).select_related("user")
    
    history_count = TeamJoinRequest.objects.filter(team=team).exclude(status="PENDING").count()

    return render(
        request,
        "teams/team_manage.html",
        {
            "team": team,
            "memberships": memberships,
            "pending_requests": pending_requests,
            "history_count": history_count,
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
                TeamMembership.objects.create(team=team, user=request.user)
                messages.success(request, f'Team "{team.name}" created successfully.')
                return redirect("team_detail", team_id=team.id)
            except IntegrityError:
                errors.append("A team with this name already exists.")

    return render(request, "teams/team_create.html", {"errors": errors})
