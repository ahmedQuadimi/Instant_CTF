from django.urls import path

from . import views

urlpatterns = [
    path("players/", views.players_list, name="players_list"),
    path("profile/<int:user_id>/", views.profile_view, name="profile"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path("users/<int:user_id>/promote/", views.admin_promote, name="admin_promote"),
]
