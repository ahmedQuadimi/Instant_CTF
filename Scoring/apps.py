from django.apps import AppConfig


class ScoringConfig(AppConfig):
    name = 'Scoring'

    def ready(self):
        import Scoring.signals  # noqa: F401
