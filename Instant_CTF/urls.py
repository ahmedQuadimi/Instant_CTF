"""
URL configuration for Instant_CTF project.
"""

from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import include, path

from . import views

urlpatterns = [
    path("admin/", admin.site.urls),

    # -----------------------------------------------------------------------
    # django-allauth
    # Handles:  /accounts/login/  /accounts/signup/  /accounts/logout/
    #           /accounts/google/login/  (OAuth2 callback)
    # -----------------------------------------------------------------------
    path("accounts/", include("allauth.urls")),
    path("accounts/", include("Accounts.urls")),
    path("dev/", views.dev_index, name="dev_index"),
    path("dev/components/", views.dev_components, name="dev_components"),
    path("dev/auth/", views.dev_auth, name="dev_auth"),
    path("dev/challenges/", views.dev_challenges, name="dev_challenges"),
    path("dev/scoreboard/", views.dev_scoreboard, name="dev_scoreboard"),
    path("dev/events/", views.dev_events, name="dev_events"),
    path("dev/forms/", views.dev_forms, name="dev_forms"),

    # -----------------------------------------------------------------------
    # Platform routes – all protected by @login_required
    # -----------------------------------------------------------------------
    path("", login_required(views.home), name="home"),
    path("about/", views.about, name="about"),
    path("orgs/", include("Organizations.urls")),
    path("teams/", include("Teams.urls")),
    path("events/", include("Events.urls")),
]
