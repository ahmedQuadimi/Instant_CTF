from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from Challenges.models import Challenge
from Events.models import Event, EventRoster
from Scoring.models import Solve
from Scoring.services import invalidate_event_scoreboard_cache


@receiver(post_save, sender=Solve)
@receiver(post_delete, sender=Solve)
def invalidate_scoreboard_for_solve(sender, instance, **kwargs):
    invalidate_event_scoreboard_cache(instance.challenge.event_id)


@receiver(post_save, sender=Challenge)
@receiver(post_delete, sender=Challenge)
def invalidate_scoreboard_for_challenge(sender, instance, **kwargs):
    invalidate_event_scoreboard_cache(instance.event_id)


@receiver(post_save, sender=EventRoster)
@receiver(post_delete, sender=EventRoster)
def invalidate_scoreboard_for_event_roster(sender, instance, **kwargs):
    invalidate_event_scoreboard_cache(instance.event_id)


@receiver(post_save, sender=Event)
@receiver(post_delete, sender=Event)
def invalidate_scoreboard_for_event(sender, instance, **kwargs):
    invalidate_event_scoreboard_cache(instance.pk)
