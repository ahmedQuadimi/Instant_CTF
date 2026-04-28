import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Instant_CTF.settings')
django.setup()

from django.contrib.auth import get_user_model
from Teams.models import Team

User = get_user_model()

# Create Captain
captain, _ = User.objects.get_or_create(username='test_captain')
captain.set_password('password123')
captain.is_staff = True
captain.is_superuser = True
captain.save()

# Create User A
user_a, _ = User.objects.get_or_create(username='test_usera')
user_a.set_password('password123')
user_a.save()

# Create Team
team, _ = Team.objects.get_or_create(name='Test Team', defaults={'captain': captain})
if team.captain != captain:
    team.captain = captain
    team.save()

print(f"Team ID: {team.id}")
