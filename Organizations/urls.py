from django.urls import path

from . import views

urlpatterns = [
    path("", views.org_home, name="organization_home"),
    path("<int:org_id>/", views.org_detail, name="organization_detail"),
    path(
        "<int:org_id>/manage/",
        views.manage_org_dashboard,
        name="manage_organization_dashboard",
    ),
]
