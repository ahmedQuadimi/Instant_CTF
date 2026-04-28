import os

try:
    os.remove('/home/ysf/S2_2025-2026/Digital_Culture/Project/Instant_CTF/Events/migrations/0004_event_creator_alter_event_visibility.py')
    print("Deleted 0004_event_creator_alter_event_visibility.py")
except Exception as e:
    print(f"Error: {e}")
