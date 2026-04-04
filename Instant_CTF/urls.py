"""
URL configuration for Instant_CTF project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path

from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    # Django Allauth (Handles /login/, /signup/, /logout/, and Google OAuth)
    path("accounts/", include("allauth.urls")),
    path("", views.home, name="home"),
    path("dev/", views.dev_index, name="dev_index"),
    path("dev/components/", views.dev_components, name="dev_components"),
    path("dev/auth/", views.dev_auth, name="dev_auth"),
    path("orgs/", include("Organizations.urls")),
    path("teams/", include("Teams.urls")),
    path("events/", include("Events.urls")),
]
