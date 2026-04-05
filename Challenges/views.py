from datetime import timedelta
import hashlib

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST

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

# Create your views here.


@login_required
def add_challenge(request, event_id):
    event = get_event_or_404(event_id)
    return render(
        request,
        "challenges/create_challenge.html",
        {
            "event": event,
            "message": "Challenge creation is managed from the event dashboard.",
        },
    )


@login_required
@require_POST
def submit_flag(request, event_id, challenge_id):
    now = timezone.now()

    roster_or_response = get_roster_or_403(request, event_id, json=True, with_team=True)
    if not isinstance(roster_or_response, EventRoster):
        return roster_or_response
    roster = roster_or_response

    event = get_event_or_404(event_id)
    if not event_is_active(event, now):
        return JsonResponse({"status": "event_inactive"}, status=403)

    challenge = Challenge.objects.filter(pk=challenge_id, event_id=event_id).first()
    if challenge is None:
        return JsonResponse({"status": "not_rostered"}, status=403)

    if not challenge_is_available(challenge, now):
        return JsonResponse({"status": "not_found", "code": 404}, status=404)

    if Solve.objects.filter(team_id=roster.team_id, challenge_id=challenge.id).exists():
        return JsonResponse({"status": "already_solved"})

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
        return JsonResponse(
            {"status": "rate_limited", "retry_after": retry_after},
            status=429,
        )

    provided_flag = (request.POST.get("flag") or "").strip()
    submitted_hash = hashlib.sha256(provided_flag.encode()).hexdigest()
    is_correct = submitted_hash == challenge.flag_hash

    submission = Submission.objects.create(
        user=request.user,
        team_id=roster.team_id,
        challenge_id=challenge.id,
        provided_flag=provided_flag,
        is_correct=is_correct,
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
        except IntegrityError:
            return JsonResponse({"status": "already_solved"})

        if not created:
            return JsonResponse({"status": "already_solved"})

        return JsonResponse({"status": "correct"})

    return JsonResponse(
        {
            "status": "incorrect",
            "attempts_remaining": max(0, 5 - recent_fail_count),
        }
    )


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
