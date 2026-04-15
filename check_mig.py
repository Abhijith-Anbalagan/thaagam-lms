import sqlite3
try:
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    c.execute("SELECT app, name FROM django_migrations WHERE app IN ('accounts', 'superadmin');")
    for row in c.fetchall():
        print(row)
except Exception as e:
    print(e)
