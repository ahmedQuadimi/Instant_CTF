from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from .models import Organization, OrganizationMembership
from .forms import OrganizationForm
from Events.models import Event

# Create your views here.


def org_home(request):
    query = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '')

    from Organizations.models import Organization, OrganizationMembership
    
    orgs = Organization.objects.annotate(
        member_count=Count('organizationmembership')
    )
    
    if query:
        orgs = orgs.filter(name__icontains=query)
    
    if request.user.is_authenticated and role_filter:
        orgs = orgs.filter(
            organizationmembership__user=request.user,
            organizationmembership__role=role_filter
        )
    
    context = {
        'orgs': orgs,
        'organizations': orgs, # Adding organizations as well since the template relies on it
        'query': query,
        'role_filter': role_filter,
    }
    return render(request, "organizations/organization_home.html", context)


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
        if action == "remove_member":
            member_id = request.POST.get("member_id", "")
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
            return redirect("manage_organization_dashboard", org_id=organization.id)
        
        elif action == "add_member":
            username = request.POST.get("username", "").strip()
            role = request.POST.get("role", "ADMIN")
            
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            try:
                user_to_add = User.objects.get(username=username)
                if OrganizationMembership.objects.filter(user=user_to_add, organization=organization).exists():
                    messages.error(request, f"{username} is already a member.")
                else:
                    if role == 'OWNER':
                        # Only owner can add another owner (or transfer)
                        requester_membership = OrganizationMembership.objects.get(user=request.user, organization=organization)
                        if requester_membership.role != 'OWNER':
                            messages.error(request, "Only owners can assign the Owner role.")
                            return redirect("manage_organization_dashboard", org_id=organization.id)
                    
                    OrganizationMembership.objects.create(
                        user=user_to_add,
                        organization=organization,
                        role=role
                    )
                    messages.success(request, f"{username} added to organization as {role}.")
            except User.DoesNotExist:
                messages.error(request, f"User '{username}' not found.")
            
            return redirect("manage_organization_dashboard", org_id=organization.id)
            
        membership_id = request.POST.get("membership_id")
        if membership_id:
            membership = get_object_or_404(
                OrganizationMembership,
                pk=membership_id
            )
            
            requester_membership = OrganizationMembership.objects.get(
                user=request.user,
                organization=membership.organization
            )
            requester_role = requester_membership.role
            
            if requester_role not in ['OWNER', 'ADMIN']:
                from django.http import HttpResponseForbidden
                return HttpResponseForbidden()
            
            new_role = request.POST.get("role")
            
            # Validation
            if new_role not in dict(OrganizationMembership.ROLE_CHOICES):
                messages.error(request, "Invalid role selected.")
                return redirect('manage_organization_dashboard', org_id=organization.id)

            if requester_role == 'ADMIN' and new_role == 'OWNER':
                messages.error(request, "Only the Owner can transfer ownership.")
                return redirect('manage_organization_dashboard', org_id=organization.id)
                
            if membership.role == 'OWNER' and requester_role != 'OWNER':
                 messages.error(request, "You cannot change the role of the Owner.")
                 return redirect('manage_organization_dashboard', org_id=organization.id)

            membership.role = new_role
            membership.save(update_fields=['role'])
            messages.success(request, f"Role for {membership.user.username} updated to {new_role}.")
            return redirect('manage_organization_dashboard', org_id=organization.id)

    memberships = OrganizationMembership.objects.filter(organization=organization).select_related("user")
    requester_role = OrganizationMembership.objects.filter(
        user=request.user,
        organization=organization
    ).values_list('role', flat=True).first()
    
    return render(
        request,
        "organizations/manage_organization_dashboard.html",
        {
            "organization": organization,
            "memberships": memberships,
            "requester_role": requester_role,
        },
    )


@login_required
def org_create(request):
    if request.method == "POST":
        form = OrganizationForm(request.POST)
        if form.is_valid():
            organization = form.save()
            OrganizationMembership.objects.create(
                user=request.user,
                organization=organization,
                role="OWNER",
            )
            messages.success(request, "Organization created successfully.")
            return redirect("organization_details", org_id=organization.id)
    else:
        form = OrganizationForm()

    return render(
        request,
        "organizations/organization_create.html",
        {"form": form},
    )


@login_required
def quick_promote_to_admin(request, org_id, user_id):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    organization = get_object_or_404(Organization, pk=org_id)
    target_user = get_object_or_404(User, pk=user_id)
    
    # Check if requester has manage access
    try:
        requester_membership = OrganizationMembership.objects.get(
            user=request.user, 
            organization=organization
        )
        if requester_membership.role not in ['OWNER', 'ADMIN']:
            messages.error(request, "You don't have permission to manage this organization.")
            return redirect('profile', user_id=user_id)
    except OrganizationMembership.DoesNotExist:
        messages.error(request, "You are not a member of this organization.")
        return redirect('profile', user_id=user_id)
    
    # Check if target is already a member
    if OrganizationMembership.objects.filter(user=target_user, organization=organization).exists():
        messages.error(request, f"{target_user.username} is already a member of this organization.")
        return redirect('profile', user_id=user_id)
    
    # Create membership as ADMIN
    OrganizationMembership.objects.create(
        user=target_user,
        organization=organization,
        role='ADMIN'
    )
    
    messages.success(request, f"{target_user.username} has been promoted to Org Admin in {organization.name}.")
    return redirect('profile', user_id=user_id)


