import sqlite3
import os

db_path = 'db.sqlite3'
if not os.path.exists(db_path):
    with open('db_info.txt', 'w') as f:
        f.write(f"Database not found at {os.path.abspath(db_path)}\n")
        f.write(f"Current working directory: {os.getcwd()}\n")
        f.write(f"Files in current dir: {os.listdir()}\n")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(Events_event)")
    columns = cursor.fetchall()
    with open('db_info.txt', 'w') as f:
        f.write(f"Columns in Events_event:\n")
        for col in columns:
            f.write(f"{col}\n")
    conn.close()
