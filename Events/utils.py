# events/utils.py (temporary)
from math import ceil

from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Event


def get_event_or_404(event_id):
    # Placeholder: simply return the event object or raise 404 if not found
    return get_object_or_404(Event, pk=event_id)


def event_has_started(event, now=None):
    now = now or timezone.now()
    return event.start_time <= now


def get_event_time_window(event):
    # Placeholder: return a simple string based on current time
    now = timezone.now()
    if now < event.start_time:
        return "upcoming"
    elif now > event.end_time:
        return "past"
    else:
        return "running"


def event_is_active(event, now=None):
    now = now or timezone.now()
    return event.start_time <= now <= event.end_time


def challenge_is_available(challenge, now=None):
    now = now or timezone.now()
    visibility = getattr(challenge, "status", getattr(challenge, "state", None))
    return (
        visibility == "VISIBLE"
        and getattr(challenge, "release_time", None) is not None
        and challenge.release_time <= now
    )


def compute_retry_after_seconds(window_seconds, oldest_failure_at, now=None):
    """
    For rate-limited responses only.
    Always returns a positive int (minimum 1).
    """
    now = now or timezone.now()
    window_seconds = int(window_seconds)

    if oldest_failure_at is None:
        return max(1, window_seconds)

    elapsed = (now - oldest_failure_at).total_seconds()
    remaining = ceil(window_seconds - elapsed)
    return max(1, remaining)
