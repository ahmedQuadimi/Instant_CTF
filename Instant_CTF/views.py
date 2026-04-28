from django.shortcuts import render
from django.utils import timezone

from Events.models import Event, EventRoster
from Scoring.models import Solve
from Teams.models import Team


def home(request):
    active_registrations = []
    if request.user.is_authenticated:
        now = timezone.now()
        active_registrations = EventRoster.objects.filter(
            user=request.user,
            event__start_time__lte=now,
            event__end_time__gte=now,
        ).select_related("event").order_by("event__end_time")[:4]

    context = {
        "events_count": Event.objects.count(),
        "teams_count": Team.objects.count(),
        "solves_count": Solve.objects.count(),
        "active_registrations": active_registrations,
    }
    return render(request, "home.html", context)


def dev_index(request):
    return render(request, "dev/index.html")


def dev_components(request):
    return render(request, "dev/components.html")


def dev_auth(request):
    return render(request, "dev/auth.html")


def dev_challenges(request):
    return render(request, "dev/challenges.html")


def dev_scoreboard(request):
    return render(request, "dev/scoreboard.html")


def dev_events(request):
    return render(request, "dev/events.html")


def dev_forms(request):
    return render(request, "dev/forms.html")


def about(request):
    return render(request, "about.html")
