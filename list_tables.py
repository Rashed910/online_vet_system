import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vetcure.settings')
django.setup()

from django.db import connection
cursor = connection.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
for t in tables:
    print(t[0])