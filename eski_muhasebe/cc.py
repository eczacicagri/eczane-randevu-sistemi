import sqlite3

conn = sqlite3.connect("ruya_eczane.db")
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("TABLOLAR:", tables)
