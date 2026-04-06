import hashlib
import secrets
from itertools import groupby

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
from .models import Event, EventRoster
from .utils import (
    event_has_started,
    get_event_or_404,
    get_event_time_window,
)

from .access import get_roster_or_403, check_event_access
from Scoring.models import Solve

# Create your views here.


_CHALLENGE_FIELD_NAMES = {field.name for field in Challenge._meta.fields}
_CHALLENGE_STATUS_FIELD = "status"


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
    events = Event.objects.select_related("organization").order_by("-start_time")

    now = timezone.now()
    event_data = []
    for evt in events:
        if now < evt.start_time:
            time_status = "upcoming"
        elif now > evt.end_time:
            time_status = "ended"
        else:
            time_status = "active"
        event_data.append({"event": evt, "time_status": time_status})

    return render(request, "events/event_list.html", {"event_data": event_data})


def event(request, event_id):
    event = get_event_or_404(event_id)
    if not check_event_access(request, event):
        return render(request, "events/event_403.html", {"event": event}, status=403)

    time_status = get_event_time_window(event)
    is_participant = False

    if request.user.is_authenticated:
        is_participant = EventRoster.objects.filter(
            user=request.user,
            event=event,
        ).exists()

    participant_count = EventRoster.objects.filter(event=event).count()
    challenge_count = Challenge.objects.filter(event=event).count()
    can_manage = _has_manage_access(request.user, event)

    return render(
        request,
        "events/event_home.html",
        {
            "event": event,
            "time_status": time_status,
            "is_participant": is_participant,
            "participant_count": participant_count,
            "challenge_count": challenge_count,
            "can_manage": can_manage,
        },
    )


def event_users(request, event_id):
    event = get_event_or_404(event_id)
    if not check_event_access(request, event):
        return render(request, "events/event_403.html", {"event": event}, status=403)

    rosters = EventRoster.objects.filter(event=event).select_related("user", "team")
    return render(
        request,
        "events/event_users.html",
        {
            "event": event,
            "rosters": rosters,
        },
    )


def event_user_details(request, event_id, user_id):
    event = get_event_or_404(event_id)
    if not check_event_access(request, event):
        return render(request, "events/event_403.html", {"event": event}, status=403)

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
    if not check_event_access(request, event):
        return render(request, "events/event_403.html", {"event": event}, status=403)

    now = timezone.now()

    if not event_has_started(event, now):
        return render(
            request,
            "events/event_not_started.html",
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

    import math

    def get_current_worth(challenge, event):
        if event.scoring_strategy == "DYNAMIC":
            return max(
                event.minimum_points or 0,
                round(
                    (event.base_points or 0)
                    * math.exp(-(event.decay_parameter or 0) * challenge.solves_count)
                ),
            )
        return event.base_points or 0

    challenges = list(Challenge.objects.filter(
        event=event,
        status="VISIBLE",
        release_time__lte=now,
    ).annotate(
        is_solved=Exists(solved_subquery)
    ).order_by("category", "release_time", "name"))

    for c in challenges:
        c.current_worth = get_current_worth(c, event)

    grouped = []
    for category, group in groupby(challenges, key=lambda c: c.category):
        grouped.append((category, list(group)))

    return render(
        request,
        "events/event_challenges.html",
        {
            "event": event,
            "challenges": challenges,
            "challenges_by_category": grouped,
        },
    )


@login_required
def register_for_event(request, event_id):
    event = get_event_or_404(event_id)
    if not check_event_access(request, event):
        return render(request, "events/event_403.html", {"event": event}, status=403)

    if request.user.is_authenticated and EventRoster.objects.filter(user=request.user, event=event).exists():
        messages.error(request, "You are already registered for this event.")
        return redirect("event_dashboard", event_id=event.id)

    if get_event_time_window(event) == "past":
        messages.error(request, "This event is over. Registration is closed.")
        return redirect("event_dashboard", event_id=event.id)

    # 2. Check if user is a team captain
    from Teams.models import Team, TeamMembership
    captain_team = Team.objects.filter(captain=request.user).first()
    
    if not captain_team:
        return render(
            request,
            "events/register_for_event.html",
            {
                "event": event,
                "is_captain": False,
                "error_message": "Only team captains can register a team. Ask your captain to register."
            },
        )

    # Fetch team members
    memberships = TeamMembership.objects.filter(team=captain_team).select_related('user')
    
    if request.method == "POST":
        selected_user_ids = request.POST.getlist("member_ids")
        # Ensure captain themselves is always included or validated
        # The user said: "Also create one for the captain themselves"
        
        # Convert to set of ints for easy handling
        selected_ids = {int(uid) for uid in selected_user_ids if uid.isdigit()}
        # Add captain if not selected
        selected_ids.add(request.user.id)
        
        # Validate count
        if event.max_team_size > 0 and len(selected_ids) > event.max_team_size:
            messages.error(request, f"You can select at most {event.max_team_size} members (including yourself).")
        else:
            # Create EventRosters
            for user_id in selected_ids:
                # Find the user instance (from the members list for safety)
                member = memberships.filter(user_id=user_id).first()
                if member or user_id == request.user.id:
                    EventRoster.objects.get_or_create(
                        user_id=user_id,
                        team=captain_team,
                        event=event
                    )
            
            messages.success(request, f"Team '{captain_team.name}' registered successfully.")
            return redirect("event_dashboard", event_id=event.id)

    slots_remaining = event.max_team_size if event.max_team_size > 0 else "Unlimited"

    return render(
        request,
        "events/register_for_event.html",
        {
            "event": event,
            "is_captain": True,
            "captain_team": captain_team,
            "memberships": memberships,
            "slots_remaining": slots_remaining,
        },
    )


@login_required
def request_join_team(request, event_id, team_id):
    event = get_event_or_404(event_id)
    if not check_event_access(request, event):
        return render(request, "events/event_403.html", {"event": event}, status=403)

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
    if not check_event_access(request, event):
        return render(request, "events/event_403.html", {"event": event}, status=403)

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


@login_required
def create_event(request):
    errors = []
    saved = False

    memberships = OrganizationMembership.objects.filter(
        user=request.user,
        role__in=("OWNER", "ADMIN"),
    ).select_related("organization")

    manageable_orgs = [membership.organization for membership in memberships]
    organizations_by_id = {organization.id: organization for organization in manageable_orgs}

    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        visibility = (request.POST.get("visibility") or "PUBLIC").strip()
        organization_id_raw = (request.POST.get("organization_id") or "").strip()
        start_raw = request.POST.get("start_time")
        end_raw = request.POST.get("end_time")
        max_team_size_raw = (request.POST.get("max_team_size") or "0").strip()

        scoring_strategy = (request.POST.get("scoring_strategy") or "STATIC").strip()
        base_points = _parse_optional_float(request.POST.get("base_points") or "500", "base_points", errors)
        minimum_points = _parse_optional_float(request.POST.get("minimum_points") or "100", "minimum_points", errors)
        decay_parameter = _parse_optional_float(request.POST.get("decay_parameter") or "0.05", "decay_parameter", errors)

        if not title:
            errors.append("Title is required.")

        try:
            organization_id = int(organization_id_raw)
        except (TypeError, ValueError):
            organization_id = None
            errors.append("A valid organization is required.")

        organization = organizations_by_id.get(organization_id)
        if organization is None:
            errors.append("You do not have permission to create events for this organization.")

        valid_visibility = {choice[0] for choice in Event.VISIBILITY_CHOICES}
        if visibility not in valid_visibility:
            errors.append("Invalid visibility.")

        start_time = _parse_optional_datetime(start_raw, errors)
        end_time = _parse_optional_datetime(end_raw, errors)

        if start_time is None:
            errors.append("start_time is required.")
        if end_time is None:
            errors.append("end_time is required.")
        if start_time is not None and end_time is not None and start_time >= end_time:
            errors.append("end_time must be after start_time.")

        try:
            max_team_size = int(max_team_size_raw)
            if max_team_size < 0:
                raise ValueError
        except (TypeError, ValueError):
            max_team_size = 0
            errors.append("max_team_size must be a non-negative integer.")

        if not errors and organization is not None and start_time is not None and end_time is not None:
            new_event = Event.objects.create(
                title=title,
                organization=organization,
                visibility=visibility,
                creator=request.user,
                scoring_strategy=scoring_strategy,
                start_time=start_time,
                end_time=end_time,
                max_team_size=max_team_size,
                base_points=int(base_points or 500),
                minimum_points=int(minimum_points or 100),
                decay_parameter=decay_parameter or 0.05,
            )
            messages.success(request, f'Event "{new_event.title}" created successfully.')
            return redirect("manage_event_dashboard", event_id=new_event.id)

    return render(
        request,
        "events/create_event.html",
        {
            "organizations": manageable_orgs,
            "errors": errors,
            "saved": saved,
        },
    )
@login_required
def generate_invite(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    # only org owner/admin can generate
    if not _has_manage_access(request.user, event):
        messages.error(request, "Not authorized.")
        return redirect("event_dashboard", event_id=event.id)

    if not event.invite_token:
        event.invite_token = secrets.token_urlsafe(32)
        event.save(update_fields=["invite_token"])

    invite_url = request.build_absolute_uri(f"/events/invite/{event.invite_token}/")
    messages.success(request, f"Invite link: {invite_url}")
    return redirect("manage_event_dashboard", event_id=event.id)


def accept_invite(request, token):
    event = get_object_or_404(Event, invite_token=token)
    if not request.user.is_authenticated:
        # store token in session, redirect to login
        request.session["pending_invite"] = token
        return redirect("account_login")

    # grant access by adding to a session whitelist
    invited = request.session.get("event_invites", [])
    if event.pk not in invited:
        invited.append(event.pk)
        request.session["event_invites"] = invited
        request.session.modified = True

    messages.success(request, f"You now have access to {event.title}.")
    return redirect("event_dashboard", event_id=event.id)

from django.core.management import call_command
from django.http import HttpResponse

@login_required
def run_migrations_view(request):
    if not request.user.is_superuser:
        return HttpResponse("Unauthorized", status=403)
    import io
    out = io.StringIO()
    try:
        call_command('migrate', 'Events', stdout=out)
        result = out.getvalue()
    except Exception as e:
        result = str(e)
    return HttpResponse(f"<pre>{result}</pre>")
