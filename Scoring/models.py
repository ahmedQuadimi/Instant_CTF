from django.conf import settings
from django.db import models

from Challenges.models import Challenge
from Teams.models import Team


# Create your models here.
class Submission(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)
    provided_flag = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [models.Index(fields=["team", "challenge", "is_correct"])]


class Solve(models.Model):
    submission = models.OneToOneField(Submission, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)
    awarded_points = models.IntegerField()
    timestamp = models.DateTimeField(db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["team", "challenge"], name="unique_solve_per_team"
            )
        ]
