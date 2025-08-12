import sqlite3

DB_PATH = 'instance/database.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("SELECT * FROM canciones")
canciones = cursor.fetchall()

print("Canciones registradas:")
print("ID | Título | Artista | Ruta Foto")
for cancion in canciones:
    print(cancion)

conn.close()
