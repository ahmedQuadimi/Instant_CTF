import hashlib
import secrets
from itertools import groupby

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.db.models import Exists, OuterRef, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from Challenges.models import Challenge
from Organizations.models import OrganizationMembership
from Teams.models import Team, TeamJoinRequest

from .forms import CreateTeamForm, JoinEventForm, EventForm, EventRegistrationForm
from Teams.forms import TeamJoinRequestForm
from .models import Event, EventRoster, EventRole
from .utils import (
    event_has_started,
    get_event_or_404,
    get_event_time_window,
)

from .access import get_roster_or_403, check_event_access
from Scoring.models import Solve
from Accounts.utils import site_admin_required

# Create your views here.


_CHALLENGE_FIELD_NAMES = {field.name for field in Challenge._meta.fields}
_CHALLENGE_STATUS_FIELD = "status"


def _has_manage_access(user, event):
    if not user.is_authenticated:
        return False

    if user.site_role == "SITE_ADMIN":
        return True

    from .models import EventRole
    try:
        er = EventRole.objects.get(user=user, event=event)
        if er.role in ('OWNER', 'ADMIN'):
            return True
    except EventRole.DoesNotExist:
        pass

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
    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "")
    org_filter = request.GET.get("org", "")

    events = (
        Event.objects.filter(visibility="PUBLIC")
        .select_related("organization")
        .order_by("-start_time")
    )

    if query:
        events = events.filter(title__icontains=query)

    now = timezone.now()
    if status_filter == "active":
        events = events.filter(start_time__lte=now, end_time__gte=now)
    elif status_filter == "upcoming":
        events = events.filter(start_time__gt=now)
    elif status_filter == "ended":
        events = events.filter(end_time__lt=now)

    if org_filter:
        events = events.filter(organization__name__icontains=org_filter)

    context = {
        "events": events,
        "query": query,
        "status_filter": status_filter,
        "org_filter": org_filter,
    }

    return render(request, "events/event_list.html", context)


def event(request, event_id):
    event = get_event_or_404(event_id)
    if not check_event_access(request, event):
        return render(request, "events/event_403.html", {"event": event}, status=403)

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

    from Events.templatetags.ui_extras import get_event_role
    requester_role = get_event_role(request.user, event)
    if not requester_role:
        from Organizations.models import OrganizationMembership
        if OrganizationMembership.objects.filter(user=request.user, organization=event.organization, role__in=("OWNER", "ADMIN")).exists():
            requester_role = "OWNER"

    user_roles = {
        role.user_id: role.role for role in EventRole.objects.filter(event=event)
    }

    team_panel_rows = [
        {
            "user": roster.user,
            "team_name": roster.team.name,
            "joined_at": roster.joined_at,
            "role": user_roles.get(roster.user_id, "PLAYER"),
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
        "saved": request.GET.get("saved") == "1",
        "requester_role": requester_role,
        "create_form": ChallengeForm(event=event),
    }

    if request.method == "POST":
        action = (request.POST.get("action") or "create").lower()

        if action == "assign_role":
            target_user_id = request.POST.get('user_id')
            new_role = request.POST.get('event_role')
            if requester_role not in ['OWNER', 'ADMIN']:
                raise PermissionDenied()
            
            if new_role == "PLAYER":
                EventRole.objects.filter(user_id=target_user_id, event=event).delete()
            else:
                EventRole.objects.update_or_create(
                    user_id=target_user_id,
                    event=event,
                    defaults={'role': new_role}
                )
            messages.success(request, "Event role updated.")
            return redirect('manage_event_dashboard', event.id)

        if action == "toggle_status":
            challenge_id = request.POST.get("challenge_id")
            challenge = get_object_or_404(Challenge, pk=challenge_id, event=event)
            requested_status = (request.POST.get("new_status") or "").strip()
            if not requested_status:
                requested_status = _toggle_status_value(challenge.status)

            if requested_status in dict(Challenge._meta.get_field('status').choices):
                challenge.status = requested_status
                challenge.save(update_fields=['status'])
                return redirect(f"/events/{event.id}/manage/?saved=1")

        if action == "create":
            form = ChallengeForm(request.POST, event=event)
            if form.is_valid():
                form.save()
                return redirect(f"/events/{event.id}/manage/?saved=1")
            context["create_form"] = form
            context["active_action"] = "create"

        elif action == "edit":
            challenge_id = request.POST.get("challenge_id")
            challenge = get_object_or_404(Challenge, pk=challenge_id, event=event)
            form = ChallengeForm(request.POST, instance=challenge, event=event)
            if form.is_valid():
                form.save()
                return redirect(f"/events/{event.id}/manage/?saved=1")
            context["edit_form"] = form
            context["editing_challenge_id"] = challenge_id
            context["active_action"] = "edit"

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
    ).filter(
        Q(release_time__isnull=True) | 
        Q(release_time__lte=now)
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

    if EventRoster.objects.filter(user=request.user, event=event).exists():
        messages.error(request, "You are already registered for this event.")
        return redirect("event_dashboard", event_id=event.id)

    if get_event_time_window(event) == "past":
        messages.error(request, "This event is over. Registration is closed.")
        return redirect("event_dashboard", event_id=event.id)

    from Teams.models import Team
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

    if request.method == "POST":
        form = EventRegistrationForm(request.POST, team=captain_team, event=event, user=request.user)
        if form.is_valid():
            member_ids = form.cleaned_data.get('member_ids', [])
            selected_ids = [int(uid) for uid in member_ids]
            selected_ids.append(request.user.id)
            
            for uid in selected_ids:
                EventRoster.objects.get_or_create(
                    user_id=uid,
                    event=event,
                    team=captain_team
                )
            messages.success(request, f"Team '{captain_team.name}' registered for {event.title}.")
            return redirect("event_dashboard", event_id=event.id)
    else:
        form = EventRegistrationForm(team=captain_team, event=event, user=request.user)

    slots_remaining = event.max_team_size if event.max_team_size > 0 else "Unlimited"

    return render(
        request,
        "events/register_for_event.html",
        {
            "event": event,
            "is_captain": True,
            "captain_team": captain_team,
            "form": form,
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

    from Teams.models import TeamMembership
    team_member_count = TeamMembership.objects.filter(team=team).count()
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
    memberships = OrganizationMembership.objects.filter(
        user=request.user,
        role__in=("OWNER", "ADMIN"),
    ).select_related("organization")

    manageable_orgs = [membership.organization for membership in memberships]

    if request.method == "POST":
        form = EventForm(request.POST, user=request.user)
        if form.is_valid():
            new_event = form.save(commit=False)
            new_event.creator = request.user
            new_event.save()
            
            EventRole.objects.create(
                user=request.user,
                event=new_event,
                role='OWNER'
            )
            messages.success(request, f'Event "{new_event.title}" created successfully.')
            return redirect("manage_event_dashboard", event_id=new_event.id)
    else:
        form = EventForm(user=request.user)

    return render(
        request,
        "events/create_event.html",
        {
            "organizations": manageable_orgs,
            "form": form,
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

@site_admin_required
def run_migrations_view(request):
    import io
    out = io.StringIO()
    try:
        call_command('migrate', 'Events', stdout=out)
        result = out.getvalue()
    except Exception as e:
        result = str(e)
    return HttpResponse(f"<pre>{result}</pre>")
