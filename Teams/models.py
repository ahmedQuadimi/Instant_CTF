from django.conf import settings
from django.db import models

# Create your models here.


class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    captain = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="captained_teams",
    )
    is_public = models.BooleanField(default=True)
    global_rating = models.FloatField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class TeamJoinRequest(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    requested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "team", "status"], name="unique_team_join_request"
            )
        ]


class TeamMembership(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="team_memberships"
    )
    team = models.ForeignKey(
        Team, 
        on_delete=models.CASCADE, 
        related_name="members"
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # A user can only be in a specific team once
            models.UniqueConstraint(
                fields=["user", "team"], 
                name="unique_team_membership"
            )
        ]

    def __str__(self):
        return f"{self.user.username} in {self.team.name}"