# Create your models here.
from django.conf import settings
from django.db import models
from django.utils import timezone

from Organizations.models import Organization
from Teams.models import Team


class Event(models.Model):
<<<<<<< HEAD
    VISIBILITY_CHOICES = [
        ("PUBLIC", "Public"),
        ("CODE", "Code"),
        ("INVITE", "Invite"),
    ]
=======
    VISIBILITY_CHOICES = [("PUBLIC", "Public"), ("PRIVATE", "Private")]
>>>>>>> 25f3b19b2af5acedc796aa6f4f38034c0dd20992
    SCORING_STRATEGIES = [
        ("STATIC", "Static"),
        ("DYNAMIC", "Dynamic"),
        ("LINEAR", "Linear"),
        ("EXPONENTIAL", "Exponential"),
    ]
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="events"
    )
    visibility = models.CharField(
        max_length=20, choices=VISIBILITY_CHOICES, default="PUBLIC"
    )
    access_code = models.CharField(max_length=50, blank=True, null=True)
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(db_index=True)
    max_team_size = models.IntegerField(default=0, help_text="0 if not limit is applicable")
    creator = models.ForeignKey(
<<<<<<< HEAD
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_events"
    )
=======
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_events"
    )

>>>>>>> 25f3b19b2af5acedc796aa6f4f38034c0dd20992

    scoring_strategy = models.CharField(
        max_length=20, choices=SCORING_STRATEGIES, default="STATIC"
    )

    decay_parameter = models.FloatField(
        default=0.05,
        help_text="The decay for which the score of a challenge is calculated based on the number of solved",
    )

    base_points = models.IntegerField(default=500, help_text="The base points")
    minimum_points = models.IntegerField(default=100, help_text="The minimum points")
    invite_token = models.CharField(
        max_length=64, blank=True, null=True, unique=True, db_index=True
    )

    def __str__(self):
        return self.title

    @property
    def time_status(self):
        now = timezone.now()
        if now < self.start_time:
            return 'upcoming'
        elif now > self.end_time:
            return 'ended'
        else:
            return 'active'
    
    @property
    def is_active(self):
        return self.time_status == 'active'
    
    @property
    def is_upcoming(self):
        return self.time_status == 'upcoming'
    
    @property
    def is_ended(self):
        return self.time_status == 'ended'


class EventRoster(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="event_rosters"
    )
    team = models.ForeignKey(
        Team, on_delete=models.CASCADE, related_name="event_rosters"
    )
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="rosters")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "event"], name="unique_event_roster"
            )
        ]

class EventRole(models.Model):
    EVENT_ROLE_CHOICES = [
        ('OWNER', 'Owner'),
        ('ADMIN', 'Admin'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='event_roles'
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='event_roles'
    )
    role = models.CharField(
        max_length=10,
        choices=EVENT_ROLE_CHOICES
    )
    assigned_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'event'],
                name='unique_event_role'
            )
        ]
