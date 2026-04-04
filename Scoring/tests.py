from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch

from Challenges.models import Challenge
from Events.models import Event, EventRoster
from Organizations.models import Organization
from Scoring.models import Solve, Submission
from Scoring.services import get_cached_ranked_teams
from Scoring.utils import calculate_event_points, calculate_linear_points, calculate_points
from Teams.models import Team


class CalculatePointsTests(SimpleTestCase):
    def test_returns_max_points_for_first_blood(self):
        self.assertEqual(calculate_points(500, 100, 0.05, 0), 500)

    def test_applies_exponential_decay(self):
        self.assertEqual(calculate_points(500, 100, 0.05, 10), 303)

    def test_never_returns_less_than_min_points(self):
        self.assertEqual(calculate_points(500, 100, 0.05, 100), 100)

    def test_linear_decay_reduces_points_until_minimum(self):
        self.assertEqual(calculate_linear_points(500, 100, 0.05, 5), 375)
        self.assertEqual(calculate_linear_points(500, 100, 0.05, 100), 100)

    def test_event_points_support_static_linear_and_exponential(self):
        self.assertEqual(calculate_event_points("STATIC", 500, 100, 0.05, 20), 500)
        self.assertEqual(calculate_event_points("LINEAR", 500, 100, 0.05, 5), 375)
        self.assertEqual(
            calculate_event_points("EXPONENTIAL", 500, 100, 0.05, 10), 303
        )


class EventScoreboardViewTests(TestCase):
    def setUp(self):
        cache.clear()
        User = get_user_model()
        now = timezone.now()

        self.user = User.objects.create_user(username="viewer", password="testpass123")
        self.owner = User.objects.create_user(username="owner", password="testpass123")
        self.player_a = User.objects.create_user(
            username="player_a", password="testpass123"
        )
        self.player_b = User.objects.create_user(
            username="player_b", password="testpass123"
        )
        self.player_c = User.objects.create_user(
            username="player_c", password="testpass123"
        )

        self.organization = Organization.objects.create(name="Org")
        self.event = Event.objects.create(
            title="Spring CTF",
            organization=self.organization,
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=1),
            scoring_strategy="EXPONENTIAL",
            base_points=500,
            minimum_points=100,
            decay_parameter=0.05,
        )

        self.team_alpha = Team.objects.create(name="Alpha", captain=self.owner)
        self.team_beta = Team.objects.create(name="Beta", captain=self.owner)
        self.team_gamma = Team.objects.create(name="Gamma", captain=self.owner)

        self.alpha_roster = EventRoster.objects.create(
            user=self.player_a,
            team=self.team_alpha,
            event=self.event,
        )
        self.beta_roster = EventRoster.objects.create(
            user=self.player_b,
            team=self.team_beta,
            event=self.event,
        )
        self.gamma_roster = EventRoster.objects.create(
            user=self.player_c,
            team=self.team_gamma,
            event=self.event,
        )
        EventRoster.objects.filter(pk=self.alpha_roster.pk).update(
            joined_at=now - timedelta(minutes=30)
        )
        EventRoster.objects.filter(pk=self.beta_roster.pk).update(
            joined_at=now - timedelta(minutes=20)
        )
        EventRoster.objects.filter(pk=self.gamma_roster.pk).update(
            joined_at=now - timedelta(minutes=10)
        )

        self.challenge_one = Challenge.objects.create(
            event=self.event,
            name="Warmup",
            category="web",
            description="desc",
            state="VISIBLE",
            flag_hash="hash1",
            solves_count=0,
        )
        self.challenge_two = Challenge.objects.create(
            event=self.event,
            name="Crypto",
            category="crypto",
            description="desc",
            state="VISIBLE",
            flag_hash="hash2",
            solves_count=5,
        )

    def _create_solve(self, team, challenge, timestamp, suffix, awarded_points):
        submission = Submission.objects.create(
            user=team.captain,
            team=team,
            challenge=challenge,
            provided_flag=f"flag-{suffix}",
            is_correct=True,
        )
        Submission.objects.filter(pk=submission.pk).update(timestamp=timestamp)
        return Solve.objects.create(
            submission=submission,
            team=team,
            challenge=challenge,
            awarded_points=awarded_points,
            timestamp=timestamp,
        )

    def test_requires_login(self):
        response = self.client.get(reverse("event_scoreboard", args=[self.event.id]))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_ranks_teams_uses_zero_solve_rows_and_refreshes_while_event_is_live(self):
        now = timezone.now()
        self._create_solve(
            self.team_alpha,
            self.challenge_one,
            now - timedelta(minutes=40),
            "a1",
            500,
        )
        self._create_solve(
            self.team_alpha,
            self.challenge_two,
            now - timedelta(minutes=15),
            "a2",
            389,
        )
        self._create_solve(
            self.team_beta,
            self.challenge_one,
            now - timedelta(minutes=25),
            "b1",
            500,
        )
        self._create_solve(
            self.team_beta,
            self.challenge_two,
            now - timedelta(minutes=5),
            "b2",
            389,
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse("event_scoreboard", args=[self.event.id]))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["event_ended"])
        self.assertNotContains(response, 'http-equiv="refresh"', html=False)
        self.assertContains(
            response,
            reverse("event_scoreboard_data", args=[self.event.id]),
            html=False,
        )

        ranked_teams = response.context["ranked_teams"]
        self.assertEqual(
            [team["team_name"] for team in ranked_teams], ["Alpha", "Beta", "Gamma"]
        )
        self.assertEqual([team["rank"] for team in ranked_teams], [1, 2, 3])
        self.assertEqual(ranked_teams[0]["score"], 889)
        self.assertEqual(ranked_teams[0]["solve_count"], 2)
        self.assertEqual(ranked_teams[1]["score"], 889)
        self.assertEqual(ranked_teams[1]["solve_count"], 2)
        self.assertEqual(ranked_teams[2]["score"], 0)
        self.assertEqual(ranked_teams[2]["solve_count"], 0)
        self.assertIsNone(ranked_teams[2]["last_solve_at"])

    def test_marks_final_standings_after_event_end(self):
        self.event.end_time = timezone.now() - timedelta(minutes=1)
        self.event.save(update_fields=["end_time"])

        self.client.force_login(self.user)
        response = self.client.get(reverse("event_scoreboard", args=[self.event.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["event_ended"])
        self.assertContains(response, "Final standings")
        self.assertNotContains(response, 'http-equiv="refresh"', html=False)

    def test_scoreboard_data_returns_live_json_payload(self):
        now = timezone.now()
        self._create_solve(
            self.team_alpha,
            self.challenge_one,
            now - timedelta(minutes=10),
            "a1",
            500,
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse("event_scoreboard_data", args=[self.event.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        payload = response.json()
        self.assertFalse(payload["event_ended"])
        self.assertEqual(payload["ranked_teams"][0]["rank"], 1)
        self.assertEqual(payload["ranked_teams"][0]["team_name"], "Alpha")
        self.assertEqual(payload["ranked_teams"][0]["score"], 500)
        self.assertEqual(payload["ranked_teams"][0]["solve_count"], 1)
        self.assertIsNotNone(payload["ranked_teams"][0]["last_solve_at"])

    def test_scoreboard_data_only_allows_get(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("event_scoreboard_data", args=[self.event.id]))
        self.assertEqual(response.status_code, 405)

    def test_ranked_teams_are_cached_until_score_affecting_data_changes(self):
        now = timezone.now()
        self._create_solve(
            self.team_alpha,
            self.challenge_one,
            now - timedelta(minutes=10),
            "a1",
            500,
        )

        first_ranked_teams = get_cached_ranked_teams(self.event)
        second_ranked_teams = get_cached_ranked_teams(self.event)

        self.assertEqual(first_ranked_teams, second_ranked_teams)

        with patch("Scoring.services._compute_ranked_teams") as mocked_compute:
            cached_ranked_teams = get_cached_ranked_teams(self.event)
            self.assertEqual(cached_ranked_teams, first_ranked_teams)
            mocked_compute.assert_not_called()

        alpha_solve = Solve.objects.get(team=self.team_alpha, challenge=self.challenge_one)
        alpha_solve.awarded_points = 430
        alpha_solve.save(update_fields=["awarded_points"])

        with patch(
            "Scoring.services._compute_ranked_teams",
            wraps=get_cached_ranked_teams.__globals__["_compute_ranked_teams"],
        ) as mocked_compute:
            refreshed_ranked_teams = get_cached_ranked_teams(self.event)
            self.assertEqual(refreshed_ranked_teams[0]["score"], 430)
            mocked_compute.assert_called_once()
