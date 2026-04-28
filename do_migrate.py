import os
import django
from django.core.management import call_command
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Instant_CTF.settings')
django.setup()
print("Starting makemigrations...")
call_command('makemigrations', 'Events')
print("Starting migrate...")
call_command('migrate', 'Events')
print("Done!")
