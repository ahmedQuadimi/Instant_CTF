from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render

from Teams.models import Team, TeamJoinRequest

from .forms import CreateTeamForm, JoinEventForm, TeamJoinRequestForm
from .models import EventRoster
from .utils import get_event_or_404, get_event_time_window

# Create your views here.


def event_list(request):
    return render(request, "events/event_list.html")


def event(request, event_id):
    event = get_event_or_404(event_id)
    time_status = get_event_time_window(event)
    is_participant = False

    if request.user.is_authenticated:
        is_participant = EventRoster.objects.filter(
            user=request.user,
            event=event,
        ).exists()

    return render(
        request,
        "events/event_home.html",
        {
            "event": event,
            "time_status": time_status,
            "is_participant": is_participant,
        },
    )


def event_users(request, event_id):
    event = get_event_or_404(event_id)
    rosters = EventRoster.objects.filter(event=event).select_related("user", "team")
    return render(
        request,
        "events/event_users.html",
        {
            "event": event,
            "rosters": rosters,
        },
    )


def event_user_detail(request, event_id, user_id):
    event = get_event_or_404(event_id)
    User = get_user_model()
    profile_user = get_object_or_404(User, pk=user_id)
    roster = get_object_or_404(EventRoster, user=profile_user, event=event)
    return render(
        request,
        "events/event_user_detail.html",
        {
            "event": event,
            "profile_user": profile_user,
            "roster": roster,
        },
    )


def manage_event_dashboard(request, event_id):
    event = get_event_or_404(event_id)
    return render(request, "events/manage_event_dashboard.html", {"event": event})


def event_challenges(request, event_id):
    event = get_event_or_404(event_id)
    return render(request, "events/event_challenges.html", {"event": event})


@login_required
def register_for_event(request, event_id):
    event = get_event_or_404(event_id)
    code_verified_session_key = f"event_{event.id}_code_verified"

    if EventRoster.objects.filter(user=request.user, event=event).exists():
        return redirect("event_dashboard", event_id=event.id)

    if get_event_time_window(event) == "past":
        messages.error(request, "This event is over. Registration is closed.")
        return redirect("event_dashboard", event_id=event.id)

    requires_access_code = event.visibility == "CODE"
    is_code_verified = request.session.get(code_verified_session_key, False)

    if requires_access_code and not is_code_verified:
        if request.method == "POST":
            join_form = JoinEventForm(request.POST)
            if join_form.is_valid():
                if join_form.cleaned_data["access_code"] == (event.access_code or ""):
                    request.session[code_verified_session_key] = True
                    return redirect("register_for_event", event_id=event.id)
                join_form.add_error("access_code", "Invalid access code.")
        else:
            join_form = JoinEventForm()

        return render(
            request,
            "events/register_for_event.html",
            {
                "event": event,
                "form": join_form,
            },
        )

    if request.method == "POST":
        create_team_form = CreateTeamForm(request.POST)
        if create_team_form.is_valid():
            try:
                team = Team.objects.create(
                    name=create_team_form.cleaned_data["name"],
                    is_public=create_team_form.cleaned_data["is_public"],
                    captain=request.user,
                )
                EventRoster.objects.create(user=request.user, team=team, event=event)
            except IntegrityError:
                create_team_form.add_error(
                    "name", "A team with this name already exists."
                )
            else:
                request.session.pop(code_verified_session_key, None)
                messages.success(request, "You have joined the event successfully.")
                return redirect("event_dashboard", event_id=event.id)
    else:
        create_team_form = CreateTeamForm()

    return render(
        request,
        "events/create_team_for_event.html",
        {
            "event": event,
            "form": create_team_form,
        },
    )


@login_required
def request_join_team(request, event_id, team_id):
    event = get_event_or_404(event_id)
    team = get_object_or_404(Team, pk=team_id)

    is_team_in_event = EventRoster.objects.filter(event=event, team=team).exists()
    if not is_team_in_event:
        messages.error(request, "This team is not participating in the selected event.")
        return redirect("event_teams", event_id=event.id)

    if EventRoster.objects.filter(user=request.user, event=event).exists():
        messages.error(request, "You are already part of a team in this event.")
        return redirect("event_dashboard", event_id=event.id)

    team_member_count = EventRoster.objects.filter(event=event, team=team).count()
    if event.max_team_size > 0 and team_member_count >= event.max_team_size:
        messages.error(request, "This team has reached the event team size limit.")
        return redirect("event_teams", event_id=event.id)

    if request.method == "POST":
        form = TeamJoinRequestForm(request.POST)
        if form.is_valid():
            _, created = TeamJoinRequest.objects.get_or_create(
                user=request.user,
                team=team,
                status="PENDING",
            )
            if created:
                messages.success(request, "Your join request has been submitted.")
            else:
                messages.info(
                    request, "You already have a pending request for this team."
                )
            return redirect("my_join_requests", event_id=event.id)
    else:
        form = TeamJoinRequestForm()

    return render(
        request,
        "events/request_join_team.html",
        {
            "event": event,
            "team": team,
            "form": form,
        },
    )


@login_required
def my_join_requests(request, event_id):
    event = get_event_or_404(event_id)
    join_requests = (
        TeamJoinRequest.objects.filter(
            user=request.user,
            team__event_rosters__event=event,
        )
        .select_related("team")
        .distinct()
    )

    return render(
        request,
        "events/my_join_requests.html",
        {
            "event": event,
            "join_requests": join_requests,
        },
    )


def create_event(request):
    return render(request, "events/create_event.html")
