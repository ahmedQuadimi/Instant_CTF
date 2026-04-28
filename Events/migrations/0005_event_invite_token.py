from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('Events', '0004_event_creator'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='invite_token',
            field=models.CharField(blank=True, db_index=True, max_length=64, null=True, unique=True),
        ),
    ]
