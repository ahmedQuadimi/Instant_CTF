from django.db import models

from Events.models import Event


# Create your models here.
class Challenge(models.Model):
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="challenges"
    )
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    description = models.TextField()
    connection_info = models.TextField(blank=True)
    state = models.CharField(
        max_length=20,
        choices=[("HIDDEN", "Hidden"), ("VISIBLE", "Visible")],
        default="HIDDEN",
    )
    flag_hash = models.CharField(max_length=128)

    release_time = models.DateTimeField(
        blank=True,
        null=True,
        db_index=True,
        help_text="Date from when the problem is going to be available .",
    )
    solves_count = models.IntegerField(default=0, db_index=True)

    class Meta:
        ordering = ["category", "release_time", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["event", "name"], name="unique_challenge_name_per_event"
            )
        ]
