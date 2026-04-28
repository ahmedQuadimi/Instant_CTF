import os
import django
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Instant_CTF.settings")
django.setup()

from django.contrib.auth import get_user_model
from Events.models import Event
from Organizations.models import Organization

User = get_user_model()

# Create users
user_a, _ = User.objects.get_or_create(username='userA', defaults={'email': 'usera@example.com'})
user_a.set_password('password123')
user_a.site_role = 'SITE_ADMIN'
user_a.save()

user_b, _ = User.objects.get_or_create(username='userB', defaults={'email': 'userb@example.com'})
user_b.set_password('password123')
user_b.save()

# Create an organization and event to test event registration
org, _ = Organization.objects.get_or_create(name='TestOrgA', defaults={'description': 'Test Org'})
event, _ = Event.objects.get_or_create(
    title='TestEventA', 
    defaults={
        'organization': org,
        'creator': user_a,
        'start_time': timezone.now() - timezone.timedelta(days=1),
        'end_time': timezone.now() + timezone.timedelta(days=1),
        'visibility': 'PUBLIC',
        'scoring_strategy': 'STATIC',
        'max_team_size': 5
    }
)

print(f"Users userA and userB created.")
print(f"Event ID: {event.id}")
