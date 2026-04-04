# events/utils.py (temporary)
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
