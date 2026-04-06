from django.shortcuts import render


def home(request):
    return render(request, "home.html")


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
