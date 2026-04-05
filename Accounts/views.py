from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from Events.models import EventRoster
from Scoring.models import Solve
from Teams.models import Team

User = get_user_model()


def profile_view(request, user_id):
    profile_user = get_object_or_404(User, pk=user_id)

    # Team memberships (via EventRoster → team)
    team_ids = (
        EventRoster.objects.filter(user=profile_user)
        .values_list("team_id", flat=True)
        .distinct()
    )
    teams = Team.objects.filter(pk__in=team_ids)

    # Events participated in
    event_rosters = (
        EventRoster.objects.filter(user=profile_user)
        .select_related("event", "team")
        .order_by("-joined_at")
    )

    # Solve count
    solve_count = Solve.objects.filter(
        team_id__in=team_ids,
        submission__user=profile_user,
    ).count()

    is_own_profile = request.user.is_authenticated and request.user.id == profile_user.id

    return render(
        request,
        "accounts/profile.html",
        {
            "profile_user": profile_user,
            "teams": teams,
            "event_rosters": event_rosters,
            "solve_count": solve_count,
            "is_own_profile": is_own_profile,
        },
    )


@login_required
def profile_edit(request):
    if request.method == "POST":
        new_username = (request.POST.get("username") or "").strip()
        if new_username:
            request.user.username = new_username
            request.user.save(update_fields=["username"])
            return redirect("profile", user_id=request.user.id)

    return render(
        request,
        "accounts/profile_edit.html",
        {"profile_user": request.user},
    )
