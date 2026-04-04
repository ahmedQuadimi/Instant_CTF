"""
Accounts/adapters.py
====================
Custom allauth adapters for Instant CTF.

Why this file exists
--------------------
When a user authenticates via Google OAuth for the first time, allauth tries
to create an account automatically.  The default behaviour skips the username
step, which would break the CTF scoreboard.

Our CTFSocialAccountAdapter intercepts pre-sign-up and:

  1. If Google provides a sensible username candidate it uses it (de-colliding
     if necessary).
  2. If it cannot derive a clean username it raises ``ImmediateHttpResponse``
     to redirect the user to the regular signup form so they can pick one
     themselves.

Roster Orphan Hook
------------------
New users – whether they register via email or Google – must join or create an
EventRoster team before they can participate in challenges.

The ``CTFSocialAccountAdapter.save_user`` method is the canonical place to
fire a post-registration signal or create a placeholder record.  The
``# TODO: ROSTER-HOOK`` comment below is the exact location where you should
add that logic.
"""

import re

from allauth.account.models import EmailAddress
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.shortcuts import redirect


class CTFSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Social account adapter that guarantees every user has a username."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _slugify_username(raw: str) -> str:
        """Return a valid Django username derived from *raw*."""
        slug = re.sub(r"[^\w.]", "_", raw).strip("_").lower()
        return slug or "user"

    def _unique_username(self, candidate: str) -> str:
        """Append a numeric suffix until the username is not taken."""
        User = get_user_model()
        base = candidate[:140]  # leave room for suffix
        username = base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}_{counter}"
            counter += 1
        return username

    # ------------------------------------------------------------------
    # allauth hooks
    # ------------------------------------------------------------------

    def populate_user(self, request, sociallogin, data):
        """
        Called by allauth to fill in user fields from the social provider's
        data *before* the user is saved.

        We derive a unique username from the Google display name / email so
        the user doesn't need to fill in the signup form for standard cases.
        """
        user = super().populate_user(request, sociallogin, data)

        if not user.username:
            # Build a candidate username from the name or the email local part
            name_candidate = (
                data.get("name")
                or data.get("first_name", "")
                or (data.get("email") or "").split("@")[0]
            )
            candidate = self._slugify_username(name_candidate)
            user.username = self._unique_username(candidate)

        return user

    def save_user(self, request, sociallogin, form=None):
        """
        Called once, right after a brand-new social user is written to the DB.

        This is the primary hook for post-registration side-effects.
        """
        user = super().save_user(request, sociallogin, form=form)

        # ----------------------------------------------------------------
        # TODO: ROSTER-HOOK
        # ----------------------------------------------------------------
        # Every new user must be linked to an EventRoster team before they
        # can see challenges.  Insert your logic here, for example:
        #
        #   from Events.models import EventRoster
        #   from Teams.models import Team
        #
        #   active_event = Event.objects.filter(status="active").first()
        #   if active_event:
        #       team = Team.objects.create(
        #           name=f"{user.username}'s team",
        #           captain=user,
        #           is_public=True,
        #       )
        #       EventRoster.objects.create(user=user, team=team, event=active_event)
        #
        # Alternatively, redirect the user to a "choose/create team" page
        # via a signal:
        #
        #   from django.db.models.signals import post_save
        #   # connect your handler in Accounts/apps.py ready()
        # ----------------------------------------------------------------

        return user
