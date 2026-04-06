import os
import shutil

pycache_dir = '/home/ysf/S2_2025-2026/Digital_Culture/Project/Instant_CTF/Events/migrations/__pycache__'
if os.path.exists(pycache_dir):
    shutil.rmtree(pycache_dir)
    print("Deleted __pycache__")
else:
    print("__pycache__ not found")
