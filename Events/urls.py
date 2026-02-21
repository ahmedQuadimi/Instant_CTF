from django.urls import path

from Challenges.views import add_challenge, submit_flag
from Scoring.views import event_scoreboard
from Teams.views import event_teams

from . import views

urlpatterns = [
    path("", views.event_list, name="event_list"),
    path('create/', views.create_event, name='create_event'),
    path("<int:event_id>/", views.event, name="event_dashboard"),
    path("<int:event_id>/challenges/", views.event_challenges, name="event_challenges"),
    path("<int:event_id>/scoreboard/", event_scoreboard, name="event_scoreboard"),
    path("<int:event_id>/teams/", event_teams, name="event_teams"),
    path("<int:event_id>/users/", views.event_users, name="event_users"),
    path('<int:event_id>/register/', views.register_for_event, name='register_for_event'),
    path(
        "<int:event_id>/challenges/<int:challenge_id>/submit/",
        submit_flag,
        name="submit_flag",
    ),
    path(
        "<int:event_id>/manage/",
        views.manage_event_dashboard,
        name="manage_event_dashboard",
    ),
    path(
        "<int:event_id>/manage/challenges/create/",
        add_challenge,
        name="create_challenge",
    ),
]
