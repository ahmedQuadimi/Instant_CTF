# Create your models here.
from django.conf import settings
from django.db import models

from Organizations.models import Organization
from Teams.models import Team


class Event(models.Model):
    VISIBILITY_CHOICES = [("PUBLIC", "Public"), ("PRIVATE", "Private")]
    SCORING_STRATEGIES = [
        ("STATIC", "Static"),
        ("LINEAR", "Linear"),
        ("EXPONENTIAL", "Exponential"),  # we can add more afterward
    ]
    title = models.CharField(max_length=255)
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
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_events"
    )

    scoring_strategy = models.CharField(
        max_length=20, choices=SCORING_STRATEGIES, default="STATIC"
    )

    decay_parameter = models.FloatField(
        default=0.05,
        help_text="The decay for which the score of a challenge is calculated based on the number of solved",
    )

    base_points = models.IntegerField(default=500, help_text="The base points")
    minimum_points = models.IntegerField(default=100, help_text="The minimum points")

    def __str__(self):
        return self.title


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
