import os
from django.conf import settings

# Force SQLite for test to avoid production DB issues
import dj_database_url

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Instant_CTF.settings")
import django
# We have to patch DATABASES before django.setup() if possible, but actually we can just overwrite the env var
os.environ['DATABASE_URL'] = 'sqlite:///db.sqlite3'

django.setup()
settings.ALLOWED_HOSTS = ['*']

from django.utils import timezone
from django.test import Client
from Accounts.models import User
from Organizations.models import Organization, OrganizationMembership
from Events.models import Event
from django.urls import reverse

client = Client(SERVER_NAME='localhost')

print("--- Running Tests ---")

# 1. /about/
try:
    response = client.get("/about/")
    if response.status_code == 200:
        content = response.content.decode("utf-8")
        assert "Mouad Bensafir" in content, "Mouad Bensafir missing"
        assert "Scoreboard & Report" in content, "Scoreboard & Report missing"
        assert "Manal Zaidi" in content, "Manal Zaidi missing"
        assert "Auth & UI" in content, "Auth & UI missing"
        print("OK: Test 1 (/about/) PASSED")
    else:
        print(f"FAIL: Test 1 (/about/) FAILED - Status {response.status_code}")
except Exception as e:
    print(f"FAIL: Test 1 Exception: {e}")

try:
    user, _ = User.objects.get_or_create(username="test_tester2", email="tester2@test.com")
    user.set_password("pass")
    user.save()

    org1, _ = Organization.objects.get_or_create(name="Public Testing Org")
    org2, _ = Organization.objects.get_or_create(name="Private Testing Org")
    OrganizationMembership.objects.get_or_create(user=user, organization=org2, role="OWNER")

    # 2. search
    client.force_login(user)
    resp = client.get("/organizations/?q=Public+Testing")
    content = resp.content.decode("utf-8")
    assert "Public Testing Org" in content
    print("OK: Test 2 (/organizations/ search) PASSED")

    # 3. filter
    resp = client.get("/organizations/?role=OWNER")
    content = resp.content.decode("utf-8")
    assert "Private Testing Org" in content
    if "Public Testing Org" in content:
        print("FAIL: Test 3 (/organizations/?role=OWNER) FAILED: Public Testing Org was displayed")
    else:
        print("OK: Test 3 (/organizations/?role=OWNER) PASSED")
except Exception as e:
    print(f"FAIL: Test 2/3 Exception: {e}")

try:
    event, _ = Event.objects.get_or_create(
        title="Testing Event For UTC",
        organization=org1,
        start_time=timezone.now(),
        end_time=timezone.now()
    )
    
    resp = client.get("/events/")
    content = resp.content.decode("utf-8")
    if "UTC" in content and "Testing Event For UTC" in content:
        print("OK: Test 4 (Event List UTC) PASSED")
    else:
        print("FAIL: Test 4 FAILED: UTC not found in /events/ or Event not found")
        
    resp = client.get(f"/events/{event.id}/")
    content = resp.content.decode("utf-8")
    if "UTC" in content:
        print("OK: Test 5 (Event Home UTC) PASSED")
    else:
        print("FAIL: Test 5 FAILED: UTC not found in event home")
except Exception as e:
    print(f"FAIL: Test 4/5 Exception: {e}")

print("--- Testing Complete ---")
