import sqlite3

conn = sqlite3.connect('demo.db')
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(spots)')
print('Spots columns in demo.db:')
for row in cursor.fetchall():
    print(f'  {row[1]} ({row[2]})')
