from datetime import timedelta
import hashlib

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.urls import reverse

from Events.access import get_roster_or_403
from Events.models import EventRoster
from Events.utils import (
    challenge_is_available,
    compute_retry_after_seconds,
    event_is_active,
    get_event_or_404,
)
from Scoring.models import Solve, Submission
from .models import Challenge
from .forms import ChallengeForm, FlagSubmissionForm

# Create your views here.


@login_required
def create_challenge(request, event_id):
    event = get_event_or_404(event_id)
    
    from Organizations.models import OrganizationMembership
    membership = OrganizationMembership.objects.filter(
        user=request.user,
        organization=event.organization,
        role__in=['OWNER','ADMIN']
    ).first()
    
    if not membership:
        messages.error(request, "Only event organizers can add challenges.")
        return redirect('event_dashboard', event_id=event.id)

    if request.method == 'POST':
        form = ChallengeForm(request.POST, event=event)
        if form.is_valid():
            challenge = form.save(commit=False)
            points = int(request.POST.get('points', form.cleaned_data.get('points', 100)))
            challenge.points = points
            challenge.save()
            messages.success(request, f"Challenge created.")
            return redirect('manage_event_dashboard', event_id=event.id)
    else:
        form = ChallengeForm(event=event)

    return render(request, 'challenges/create_challenge.html', {'event': event, 'form': form})


@login_required
@require_POST
def submit_flag(request, event_id, challenge_id):
    now = timezone.now()

    roster_or_response = get_roster_or_403(request, event_id, json=False, with_team=True)
    if not isinstance(roster_or_response, EventRoster):
        return roster_or_response
    roster = roster_or_response

    event = get_event_or_404(event_id)
    if not event_is_active(event, now):
        return JsonResponse({"status": "event_inactive"}, status=403)

    challenge = Challenge.objects.filter(pk=challenge_id, event_id=event_id).first()
    if challenge is None:
        messages.error(request, "Challenge not found.")
        return redirect("event_challenges", event_id=event.id)

    if not challenge_is_available(challenge, now):
        messages.error(request, "Challenge is not yet available.")
        return redirect("event_challenges", event_id=event.id)

    if Solve.objects.filter(team_id=roster.team_id, challenge_id=challenge.id).exists():
        messages.info(request, "Challenge already solved by your team.")
        return redirect(reverse("event_challenges", args=[event.id]) + f"#challenge-{challenge.id}")

    window_start = now - timedelta(seconds=60)
    recent_fails = Submission.objects.filter(
        user=request.user,
        challenge_id=challenge.id,
        is_correct=False,
        timestamp__gte=window_start,
    ).order_by("timestamp")
    recent_fail_count = recent_fails.count()

    if recent_fail_count >= 5:
        oldest_failure = recent_fails.first()
        retry_after = compute_retry_after_seconds(60, oldest_failure.timestamp, now)
        messages.error(request, f"Too many failures. Please try again in {retry_after} seconds.")
        return redirect(reverse("event_challenges", args=[event.id]) + f"#challenge-{challenge.id}")

    if request.method == "POST":
        form = FlagSubmissionForm(request.POST)
        if form.is_valid():
            provided_flag = form.cleaned_data['flag'].strip()
            submitted_hash = hashlib.sha256(provided_flag.encode()).hexdigest()
            is_correct = submitted_hash == challenge.flag_hash

            submission = Submission.objects.create(
                user=request.user,
                team_id=roster.team_id,
                challenge_id=challenge.id,
<<<<<<< HEAD
                defaults={
                    "submission": submission,
                    "awarded_points": challenge.current_worth,
                    "timestamp": now,
                },
=======
                provided_flag=provided_flag,
                is_correct=is_correct,
>>>>>>> 25f3b19b2af5acedc796aa6f4f38034c0dd20992
            )

            if is_correct:
                Challenge.objects.filter(pk=challenge.id).update(solves_count=F("solves_count") + 1)
                try:
                    _, created = Solve.objects.get_or_create(
                        team_id=roster.team_id,
                        challenge_id=challenge.id,
                        defaults={
                            "submission": submission,
                            "awarded_points": getattr(challenge, "points", 0),
                            "timestamp": now,
                        },
                    )
                    if not created:
                        messages.info(request, "Challenge already solved by your team.")
                        return redirect(reverse("event_challenges", args=[event.id]) + f"#challenge-{challenge.id}")
                except IntegrityError:
                    messages.info(request, "Challenge already solved by your team.")
                    return redirect(reverse("event_challenges", args=[event.id]) + f"#challenge-{challenge.id}")

                messages.success(request, "Correct! Challenge solved.")
                return redirect(reverse("event_challenges", args=[event.id]) + f"#challenge-{challenge.id}")

            messages.error(request, f"Incorrect flag. {4 - recent_fail_count} attempts remaining this minute.")
            return redirect(reverse("event_challenges", args=[event.id]) + f"#challenge-{challenge.id}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")
            return redirect(reverse("event_challenges", args=[event.id]) + f"#challenge-{challenge.id}")

    return redirect(reverse("event_challenges", args=[event.id]) + f"#challenge-{challenge.id}")


def challenge_details_json(request, event_id, challenge_id):
    challenge = Challenge.objects.select_related("event").filter(pk=challenge_id).first()
    if challenge is None:
        return JsonResponse({"status": "not_found", "code": 404}, status=404)

    if challenge.event_id != event_id:
        return JsonResponse({"status": "forbidden", "code": 403}, status=403)

    roster_or_response = get_roster_or_403(request, challenge.event_id, json=True, with_team=False)
    if not isinstance(roster_or_response, EventRoster):
        return roster_or_response

    if not challenge_is_available(challenge, timezone.now()):
        return JsonResponse({"status": "not_found", "code": 404}, status=404)

    attachment_url = None  # file upload/download feature removed

    return JsonResponse(
        {
            "id": challenge.id,
            "name": challenge.name,
            "description": challenge.description,
            "connection_info": getattr(challenge, "connection_info", None),
            "attachment_url": attachment_url,
        }
    )
