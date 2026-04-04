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

    # -----------------------------------------------------------------------
    # Platform routes – all protected by @login_required
    # -----------------------------------------------------------------------
    path("", login_required(views.home), name="home"),
    path("orgs/", include("Organizations.urls")),
    path("teams/", include("Teams.urls")),
    path("events/", include("Events.urls")),
]
