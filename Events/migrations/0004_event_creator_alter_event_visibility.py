import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def backfill_event_creator(apps, schema_editor):
    Event = apps.get_model("Events", "Event")
    OrganizationMembership = apps.get_model("Organizations", "OrganizationMembership")
    app_label, model_name = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(app_label, model_name)

    fallback_user = User.objects.order_by("id").first()
    if fallback_user is None:
        fallback_user = User.objects.create(username="__migration_system__")

    role_priority = {"OWNER": 0, "ADMIN": 1, "AUTHOR": 2}

    for event in Event.objects.filter(creator__isnull=True).iterator():
        memberships = list(
            OrganizationMembership.objects.filter(organization_id=event.organization_id)
            .order_by("joined_at", "id")
            .values_list("role", "user_id")
        )

        memberships.sort(key=lambda item: (role_priority.get(item[0], 99), item[1]))
        creator_id = memberships[0][1] if memberships else fallback_user.id
        Event.objects.filter(pk=event.pk).update(creator_id=creator_id)


class Migration(migrations.Migration):

    dependencies = [
        ("Organizations", "0002_alter_organizationmembership_unique_together_and_more"),
        ("Events", "0003_event_max_team_size"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="creator",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="created_events",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(backfill_event_creator, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="event",
            name="creator",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="created_events",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="event",
            name="visibility",
            field=models.CharField(
                choices=[("PUBLIC", "Public"), ("CODE", "Code"), ("INVITE", "Invite")],
                default="PUBLIC",
                max_length=20,
            ),
        ),
    ]
