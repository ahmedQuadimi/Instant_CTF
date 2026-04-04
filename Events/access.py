from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import NoReverseMatch, reverse

from .models import EventRoster


def is_user_rostered_for_event(request, event_id):
    if not getattr(request.user, "is_authenticated", False):
        return False
    return EventRoster.objects.filter(user=request.user, event_id=event_id).exists()


def get_roster_or_403(request, event_id, *, json=False, with_team=True):
    if not getattr(request.user, "is_authenticated", False):
        if json:
            return JsonResponse({"status": "not_rostered", "code": 467}, status=403)
        messages.error(request, "You must be registered for this event to access this page.")
        try:
            return redirect(reverse("register_for_event", kwargs={"event_id": event_id}))
        except NoReverseMatch:
            return redirect(f"/events/{event_id}/register/")

    try:
        qs = EventRoster.objects
        if with_team:
            qs = qs.select_related("team")
        return qs.get(user=request.user, event_id=event_id)
    except EventRoster.DoesNotExist:
        if json:
            return JsonResponse({"status": "not_rostered", "code": 467}, status=403)

        messages.error(request, "You must be registered for this event to access this page.")
        try:
            return redirect(reverse("register_for_event", kwargs={"event_id": event_id}))
        except NoReverseMatch:
            return redirect(f"/events/{event_id}/register/")
