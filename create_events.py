import os
import django
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Instant_CTF.settings')
django.setup()

from Events.models import Event
from Organizations.models import Organization
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.first()

org, _ = Organization.objects.get_or_create(name='Test Organization')

now = timezone.now()

# Event 1: Upcoming
Event.objects.create(
    title='Upcoming Event',
    organization=org,
    start_time=now + timedelta(days=1),
    end_time=now + timedelta(days=2),
    creator=user,
    visibility='PUBLIC'
)

# Event 2: Active
Event.objects.create(
    title='Active Event',
    organization=org,
    start_time=now - timedelta(days=1),
    end_time=now + timedelta(days=1),
    creator=user,
    visibility='PUBLIC'
)

# Event 3: Ended
Event.objects.create(
    title='Ended Event',
    organization=org,
    start_time=now - timedelta(days=2),
    end_time=now - timedelta(days=1),
    creator=user,
    visibility='PUBLIC'
)

print("Created 3 test events")
