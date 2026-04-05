from django.urls import path

from . import views

urlpatterns = [
    path("", views.org_home, name="organization_home"),
    path("create/", views.org_create, name="organization_create"),
    path("<int:org_id>/", views.org_details, name="organization_details"),
    path("<int:org_id>/", views.org_details, name="organization_detail"),
    path(
        "<int:org_id>/manage/",
        views.manage_org_dashboard,
        name="manage_organization_dashboard",
    ),
]
