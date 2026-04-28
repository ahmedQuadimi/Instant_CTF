from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from Events.models import EventRoster
from Scoring.models import Solve
from Teams.models import Team
from .forms import ProfileForm

User = get_user_model()


def profile_view(request, user_id):
    profile_user = get_object_or_404(User, pk=user_id)

    # Events — all EventRoster entries
    event_rosters = EventRoster.objects.filter(
        user=profile_user
    ).select_related('event', 'team').order_by(
        '-event__start_time'
    )

    # Teams — all TeamMembership entries plus teams where user is captain
    from Teams.models import TeamMembership, Team
    team_memberships = TeamMembership.objects.filter(
        user=profile_user
    ).select_related('team')

    captained_teams = Team.objects.filter(
        captain=profile_user
    )

    # Orgs — all OrganizationMembership entries
    from Organizations.models import OrganizationMembership
    org_memberships = OrganizationMembership.objects.filter(
        user=profile_user
    ).select_related('organization')

    # Total unique teams count for the tab label and stat box
    total_team_count = captained_teams.count() + team_memberships.exclude(
        team__in=captained_teams
    ).count()

    # Solve count
    solve_count = Solve.objects.filter(
        team_id__in=team_memberships.values_list('team_id', flat=True),
        submission__user=profile_user,
    ).count()

    is_own_profile = request.user.is_authenticated and request.user.id == profile_user.id

    # Manageable Orgs (where requester is OWNER/ADMIN and target is NOT a member)
    manageable_orgs = []
    if request.user.is_authenticated and not is_own_profile:
        from Organizations.models import Organization, OrganizationMembership
        
        # Orgs the requester can manage
        requester_org_ids = OrganizationMembership.objects.filter(
            user=request.user, 
            role__in=['OWNER', 'ADMIN']
        ).values_list('organization_id', flat=True)
        
        # Orgs the target is already in
        target_org_ids = OrganizationMembership.objects.filter(
            user=profile_user
        ).values_list('organization_id', flat=True)
        
        # Difference
        promotable_ids = set(requester_org_ids) - set(target_org_ids)
        if promotable_ids:
            manageable_orgs = Organization.objects.filter(id__in=promotable_ids)

    context = {
        "profile_user": profile_user,
        "event_rosters": event_rosters,
        "team_memberships": team_memberships,
        "captained_teams": captained_teams,
        "total_team_count": total_team_count,
        "org_memberships": org_memberships,
        "solve_count": solve_count,
        "is_own_profile": is_own_profile,
        "manageable_orgs": manageable_orgs,
    }

    return render(request, "accounts/profile.html", context)


@login_required
def profile_edit(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("profile", user_id=request.user.id)
    else:
        form = ProfileForm(instance=request.user)

    return render(
        request,
        "accounts/profile_edit.html",
        {"profile_user": request.user, "form": form},
    )


def players_list(request):
    query = request.GET.get("q", "").strip()
    role_filter = request.GET.get("role", "")

    from Accounts.models import User

    players = User.objects.annotate(
        team_count=Count("team_memberships__team", distinct=True)
    ).order_by("username")

    if query:
        players = players.filter(username__icontains=query)

    if role_filter:
        players = players.filter(site_role=role_filter)

    return render(
        request,
        "accounts/players.html",
        {
            "players": players,
            "query": query,
            "role_filter": role_filter,
            "role_choices": User.ROLE_CHOICES,
        },
    )

from Accounts.utils import site_admin_required
from django.contrib import messages

@site_admin_required
def admin_promote(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        target.site_role = 'SITE_ADMIN'
        target.save(update_fields=['site_role'])
        messages.success(request, f"{target.username} is now a Site Admin.")
        return redirect('profile', user_id)
    return redirect('profile', user_id)
