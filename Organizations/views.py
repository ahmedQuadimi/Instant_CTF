from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from .models import Organization, OrganizationMembership
from Events.models import Event

# Create your views here.


def org_home(request):
    organizations = Organization.objects.annotate(member_count=Count("members", distinct=True)).order_by("name")
    return render(request, "organizations/organization_home.html", {"organizations": organizations})


def org_details(request, org_id):
    organization = get_object_or_404(Organization, pk=org_id)
    memberships = OrganizationMembership.objects.filter(organization=organization).select_related("user")
    can_manage = False
    if request.user.is_authenticated:
        can_manage = OrganizationMembership.objects.filter(
            user=request.user,
            organization=organization,
            role__in=("OWNER", "ADMIN"),
        ).exists()

    events = Event.objects.filter(organization=organization).order_by("-start_time")

    return render(
        request,
        "organizations/organization_detail.html",
        {
            "organization": organization,
            "memberships": memberships,
            "can_manage": can_manage,
            "events": events,
        },
    )


@login_required
def manage_org_dashboard(request, org_id):
    organization = get_object_or_404(Organization, pk=org_id)
    has_manage_access = OrganizationMembership.objects.filter(
        user=request.user,
        organization=organization,
        role__in=("OWNER", "ADMIN"),
    ).exists()
    if not has_manage_access:
        raise Http404("Organization not found.")

    if request.method == "POST":
        action = request.POST.get("action", "")
        member_id = request.POST.get("member_id", "")

        if action == "role_change" and member_id:
            new_role = request.POST.get("new_role", "")
            if new_role in ("ADMIN", "MEMBER"):
                try:
                    membership = OrganizationMembership.objects.get(
                        pk=int(member_id), organization=organization
                    )
                    if membership.role == "OWNER":
                        messages.error(request, "Cannot change the owner's role.")
                    else:
                        membership.role = new_role
                        membership.save(update_fields=["role"])
                        messages.success(
                            request,
                            f"{membership.user.username}'s role updated to {new_role}.",
                        )
                except (OrganizationMembership.DoesNotExist, ValueError):
                    messages.error(request, "Member not found.")
            else:
                messages.error(request, "Invalid role.")

        elif action == "remove_member" and member_id:
            try:
                membership = OrganizationMembership.objects.get(
                    pk=int(member_id), organization=organization
                )
                if membership.role == "OWNER":
                    messages.error(request, "Cannot remove the owner.")
                else:
                    username = membership.user.username
                    membership.delete()
                    messages.success(request, f"{username} has been removed.")
            except (OrganizationMembership.DoesNotExist, ValueError):
                messages.error(request, "Member not found.")

        return redirect("manage_org_dashboard", org_id=organization.id)

    memberships = OrganizationMembership.objects.filter(organization=organization).select_related("user")
    return render(
        request,
        "organizations/manage_organization_dashboard.html",
        {
            "organization": organization,
            "memberships": memberships,
        },
    )


@login_required
def org_create(request):
    errors = []
    saved = False

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        description = (request.POST.get("description") or "").strip()

        if not name:
            errors.append("Organization name is required.")

        if not errors:
            try:
                organization = Organization.objects.create(name=name, description=description)
                OrganizationMembership.objects.create(
                    user=request.user,
                    organization=organization,
                    role="OWNER",
                )
                if request.user.site_role == "PLAYER":
                    request.user.site_role = "EVENT_OWNER"
                    request.user.save(update_fields=["site_role"])
                saved = True
                messages.success(request, "Organization created successfully.")
                return redirect("organization_details", org_id=organization.id)
            except IntegrityError:
                errors.append("An organization with this name already exists.")

    return render(
        request,
        "organizations/organization_create.html",
        {"errors": errors, "saved": saved},
    )


