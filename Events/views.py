import hashlib

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from Challenges.models import Challenge
from Organizations.models import OrganizationMembership
from Teams.models import Team, TeamJoinRequest

from .forms import CreateTeamForm, JoinEventForm, TeamJoinRequestForm
from .models import EventRoster
from .utils import (
    event_has_started,
    get_event_or_404,
    get_event_time_window,
)

from .access import get_roster_or_403
from Challenges.models import Challenge
from Scoring.models import Solve

# Create your views here.


_CHALLENGE_FIELD_NAMES = {field.name for field in Challenge._meta.fields}
_CHALLENGE_STATUS_FIELD = "status" if "status" in _CHALLENGE_FIELD_NAMES else "state"


def _has_manage_access(user, event):
    if not user.is_authenticated:
        return False

    return OrganizationMembership.objects.filter(
        user=user,
        organization=event.organization,
        role__in=("OWNER", "ADMIN"),
    ).exists()


def _parse_optional_float(raw_value, field_name, errors):
    if raw_value in (None, ""):
        return None

    try:
        return float(raw_value)
    except (TypeError, ValueError):
        errors.append(f"{field_name} must be a number.")
        return None


def _parse_optional_datetime(raw_value, errors):
    if raw_value in (None, ""):
        return None

    parsed = parse_datetime(raw_value)
    if parsed is None:
        errors.append("release_time must be a valid datetime.")
        return None

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())

    return parsed


def _toggle_status_value(current_status):
    if current_status == "VISIBLE":
        return "HIDDEN"
    return "VISIBLE"


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

    if not _has_manage_access(request.user, event):
        raise PermissionDenied

    rosters = (
        EventRoster.objects.filter(event=event)
        .select_related("team", "user")
        .order_by("team__name", "joined_at")
    )

    team_counts = {}
    for roster in rosters:
        team_counts[roster.team_id] = team_counts.get(roster.team_id, 0) + 1

    team_panel_rows = [
        {
            "team_name": roster.team.name,
            "member_count": team_counts.get(roster.team_id, 0),
            "joined_at": roster.joined_at,
        }
        for roster in rosters
    ]

    challenges = event.challenges.all().order_by("category", "release_time", "name")

    context = {
        "event": event,
        "team_panel_rows": team_panel_rows,
        "challenges": challenges,
        "status_field": _CHALLENGE_STATUS_FIELD,
        "challenge_status_choices": Challenge._meta.get_field(
            _CHALLENGE_STATUS_FIELD
        ).choices,
        "form_errors": [],
        "saved": request.GET.get("saved") == "1",
    }

    if request.method == "POST":
        action = (request.POST.get("action") or "create").lower()

        if action == "toggle_status":
            challenge_id = request.POST.get("challenge_id")
            challenge = get_object_or_404(Challenge, pk=challenge_id, event=event)
            valid_status_values = {
                choice[0]
                for choice in Challenge._meta.get_field(_CHALLENGE_STATUS_FIELD).choices
            }

            requested_status = (request.POST.get("new_status") or "").strip()
            if not requested_status:
                requested_status = _toggle_status_value(
                    getattr(challenge, _CHALLENGE_STATUS_FIELD, "HIDDEN")
                )

            if requested_status in valid_status_values:
                setattr(challenge, _CHALLENGE_STATUS_FIELD, requested_status)
                challenge.save(update_fields=[_CHALLENGE_STATUS_FIELD])
                return redirect(f"/events/{event.id}/manage/?saved=1")

            context["form_errors"].append("Invalid status value.")

        challenge_id = request.POST.get("challenge_id")
        editing_challenge = None

        if action == "edit":
            if not challenge_id:
                context["form_errors"].append("challenge_id is required for edit.")
            else:
                editing_challenge = get_object_or_404(
                    Challenge,
                    pk=challenge_id,
                    event=event,
                )
        elif action != "create":
            context["form_errors"].append("Invalid action.")

        challenge = editing_challenge or Challenge(event=event)

        name = (request.POST.get("name") or "").strip()
        category = (request.POST.get("category") or "").strip()
        description = (request.POST.get("description") or "").strip()
        connection_info = (request.POST.get("connection_info") or "").strip()
        status_value = (request.POST.get(_CHALLENGE_STATUS_FIELD) or "").strip()
        raw_flag = (request.POST.get("raw_flag") or "").strip()
        release_time_raw = request.POST.get("release_time")

        min_points = _parse_optional_float(
            request.POST.get("min_points"),
            "min_points",
            context["form_errors"],
        )
        max_points = _parse_optional_float(
            request.POST.get("max_points"),
            "max_points",
            context["form_errors"],
        )
        decay_factor = _parse_optional_float(
            request.POST.get("decay_factor"),
            "decay_factor",
            context["form_errors"],
        )

        if (
            min_points is not None
            and max_points is not None
            and min_points >= max_points
        ):
            context["form_errors"].append(
                "min_points must be strictly less than max_points."
            )

        if decay_factor is not None and decay_factor <= 0:
            context["form_errors"].append("decay_factor must be greater than 0.")

        release_time = _parse_optional_datetime(
            release_time_raw, context["form_errors"]
        )

        if not name:
            context["form_errors"].append("name is required.")
        if not category:
            context["form_errors"].append("category is required.")
        if not description:
            context["form_errors"].append("description is required.")

        if action == "create" and not raw_flag:
            context["form_errors"].append(
                "raw_flag is required when creating a challenge."
            )

        valid_status_values = {
            choice[0]
            for choice in Challenge._meta.get_field(_CHALLENGE_STATUS_FIELD).choices
        }
        if status_value and status_value not in valid_status_values:
            context["form_errors"].append("Invalid status value.")

        if not context["form_errors"]:
            challenge.name = name
            challenge.category = category
            challenge.description = description

            if "connection_info" in _CHALLENGE_FIELD_NAMES:
                challenge.connection_info = connection_info

            if _CHALLENGE_STATUS_FIELD in _CHALLENGE_FIELD_NAMES and status_value:
                setattr(challenge, _CHALLENGE_STATUS_FIELD, status_value)

            if release_time_raw in (None, ""):
                challenge.release_time = None
            else:
                challenge.release_time = release_time

            for field_name, field_value in (
                ("min_points", min_points),
                ("max_points", max_points),
                ("decay_factor", decay_factor),
            ):
                if field_name in _CHALLENGE_FIELD_NAMES and field_value is not None:
                    setattr(challenge, field_name, field_value)

            if raw_flag:
                challenge.flag_hash = hashlib.sha256(
                    raw_flag.strip().encode()
                ).hexdigest()

            challenge.save()
            return redirect(f"/events/{event.id}/manage/?saved=1")

    return render(request, "events/manage_event_dashboard.html", context)


def event_challenges(request, event_id):
    event = get_event_or_404(event_id)
    now = timezone.now()

    if not event_has_started(event, now):
        return render(
            request,
            "event_not_started.html",
            {"event": event, "message": "Event hasn't started yet"},
        )

    roster_or_response = get_roster_or_403(request, event_id, json=False)
    if not isinstance(roster_or_response, EventRoster):
        return roster_or_response
    roster = roster_or_response

    solved_subquery = Solve.objects.filter(
        challenge_id=OuterRef("pk"),
        team_id=roster.team_id,
    )

    challenges = Challenge.objects.filter(
        event=event,
        state="VISIBLE",
        release_time__lte=now,
    ).annotate(
        is_solved=Exists(solved_subquery)
    )

    return render(
        request,
        "event_challenges.html",
        {"event": event, "challenges": challenges},
    )


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
