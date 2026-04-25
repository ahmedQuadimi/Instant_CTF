from django.utils import timezone
from django.test import Client
from Accounts.models import User
from Organizations.models import Organization, OrganizationMembership
from Events.models import Event
from django.urls import reverse

client = Client()

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

# Try to find url for organizations
org_list_url = "/organizations/"
try:
    reverse('organization_home')
    org_list_url = reverse('organization_home')
except:
    pass

try:
    user, _ = User.objects.get_or_create(username="test_tester", email="tester@test.com")
    user.set_password("pass")
    user.save()

    org1, _ = Organization.objects.get_or_create(name="Public Testing Org")
    org2, _ = Organization.objects.get_or_create(name="Private Testing Org")
    OrganizationMembership.objects.get_or_create(user=user, organization=org2, role="OWNER")

    # 2. search
    client.force_login(user)
    resp = client.get(org_list_url + "?q=Public+Testing")
    content = resp.content.decode("utf-8")
    assert "Public Testing Org" in content
    print("OK: Test 2 (/organizations/ search) PASSED")

    # 3. filter
    resp = client.get(org_list_url + "?role=OWNER")
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
    
    events_url = "/events/"
    try:
        events_url = reverse("event_list")
    except:
        pass

    resp = client.get(events_url)
    content = resp.content.decode("utf-8")
    if "UTC" in content and "Testing Event For UTC" in content:
        print("OK: Test 4 (Event List UTC) PASSED")
    else:
        print("FAIL: Test 4 FAILED: UTC not found in /events/ or Event not found")
        
    event_url = f"/events/{event.id}/"
    try:
        event_url = reverse("event_dashboard", args=[event.id])
    except:
        pass

    resp = client.get(event_url)
    content = resp.content.decode("utf-8")
    if "UTC" in content:
        print("OK: Test 5 (Event Home UTC) PASSED")
    else:
        print("FAIL: Test 5 FAILED: UTC not found in event home")

except Exception as e:
    print(f"FAIL: Test 4/5 Exception: {e}")

print("--- Testing Complete ---")
