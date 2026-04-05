from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from Challenges.models import Challenge
from Events.models import Event, EventRoster
from Scoring.models import Solve
from Scoring.services import invalidate_event_scoreboard_cache, _dynamic_points


@receiver(post_save, sender=Challenge)
def initialize_challenge_current_worth(sender, instance, created, **kwargs):
    """Initialize current_worth to event's base_points when challenge is created."""
    if created and instance.current_worth == 0:
        instance.current_worth = instance.event.base_points
        instance.save(update_fields=["current_worth"])


@receiver(post_save, sender=Solve)
def update_challenge_current_worth(sender, instance, created, **kwargs):
    """Update the current_worth of a challenge when a new solve is recorded."""
    if created:
        challenge = instance.challenge
        event = challenge.event
        
        # Get scoring parameters from the event
        base_points = event.base_points
        min_points = event.minimum_points
        decay_factor = event.decay_parameter
        
        # Calculate new current_worth based on current solves count
        new_worth = _dynamic_points(
            base_points, min_points, decay_factor, challenge.solves_count
        )
        challenge.current_worth = new_worth
        challenge.save(update_fields=["current_worth"])


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
