from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from Organizations.models import Organization, OrganizationMembership

from .models import Event


class CreateEventViewTests(TestCase):
    def test_create_event_sets_creator(self):
        user = get_user_model().objects.create_user(
            username="organizer",
            password="password123",
        )
        organization = Organization.objects.create(name="Org", description="Test")
        OrganizationMembership.objects.create(
            user=user,
            organization=organization,
            role="ADMIN",
        )

        self.client.force_login(user)

        response = self.client.post(
            reverse("create_event"),
            {
                "title": "Spring CTF",
                "organization_id": str(organization.id),
                "visibility": "CODE",
                "access_code": "secret",
                "start_time": "2026-04-05T12:00:00",
                "end_time": "2026-04-06T12:00:00",
                "max_team_size": "4",
            },
        )

        self.assertEqual(response.status_code, 302)

        event = Event.objects.get(title="Spring CTF")
        self.assertEqual(event.creator, user)
        self.assertEqual(event.visibility, "CODE")
        self.assertEqual(event.access_code, "secret")
