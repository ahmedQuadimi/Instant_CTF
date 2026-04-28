from django.urls import path

from Challenges.views import create_challenge, submit_flag, challenge_details_json, download_challenge_attachment
from Scoring.views import event_scoreboard, event_scoreboard_data
from Teams.views import event_teams, team_details

from . import views

urlpatterns = [
    path("", views.event_list, name="event_list"),
    path("create/", views.create_event, name="create_event"),
    path("<int:event_id>/edit/", views.edit_event, name="edit_event"),
    path("<int:event_id>/", views.event, name="event_dashboard"),
    path("<int:event_id>/challenges/", views.event_challenges, name="event_challenges"),
    path("<int:event_id>/scoreboard/", event_scoreboard, name="event_scoreboard"),
    path(
        "<int:event_id>/scoreboard/data/",
        event_scoreboard_data,
        name="event_scoreboard_data",
    ),
    path("<int:event_id>/teams/", event_teams, name="event_teams"),
    path("<int:event_id>/teams/<int:team_id>/", team_details, name="event_team_details"),
    path("<int:event_id>/teams/<int:team_id>/", team_details, name="event_team_detail"),
    path(
        "<int:event_id>/teams/<int:team_id>/request-join/",
        views.request_join_team,
        name="request_join_team",
    ),
    path(
        "<int:event_id>/my-requests/", views.my_join_requests, name="my_join_requests"
    ),
    path("<int:event_id>/users/", views.event_users, name="event_users"),
    path(
        "<int:event_id>/users/<int:user_id>/",
        views.event_user_details,
        name="event_user_details",
    ),
    path(
        "<int:event_id>/users/<int:user_id>/",
        views.event_user_details,
        name="event_user_detail",
    ),
    path(
        "<int:event_id>/register/",
        views.register_for_event,
        name="register_for_event",
    ),
    path(
        "<int:event_id>/challenges/<int:challenge_id>/submit/",
        submit_flag,
        name="submit_flag",
    ),
    path(
        "<int:event_id>/challenges/<int:challenge_id>/details/",
        challenge_details_json,
        name="challenge_details_json",
    ),
    path(
        "<int:event_id>/challenges/<int:challenge_id>/details/",
        challenge_details_json,
        name="challenge_detail_json",
    ),
    path(
        "<int:event_id>/challenges/<int:challenge_id>/attachment/",
        download_challenge_attachment,
        name="challenge_attachment",
    ),
    path(
        "<int:event_id>/manage/",
        views.manage_event_dashboard,
        name="manage_event_dashboard",
    ),
    path(
        "<int:event_id>/manage/challenges/create/",
        create_challenge,
        name="create_challenge",
    ),
    path("invite/<str:token>/", views.accept_invite, name="accept_invite"),
    path("maintenance/migrate/", views.run_migrations_view, name="run_migrations"),
    path("<int:event_id>/generate-invite/", views.generate_invite, name="generate_invite"),
]
