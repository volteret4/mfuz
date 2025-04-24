import sqlite3

# Conectar a ambas bases de datos
conn_copia = sqlite3.connect('base_copia.db')
conn_original = sqlite3.connect('base_original.db')

# Asegurarte que las tablas existen en la base original
cursor_original = conn_original.cursor()
cursor_original.execute('''
CREATE TABLE IF NOT EXISTS album_links (
    id INTEGER PRIMARY KEY,
    album_id INTEGER NOT NULL,
    service_name TEXT NOT NULL,
    url TEXT NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (album_id) REFERENCES albums(id)
)
''')

cursor_original.execute('''
CREATE TABLE IF NOT EXISTS album_reviews (
    id INTEGER PRIMARY KEY,
    album_id INTEGER NOT NULL,
    source TEXT NOT NULL,
    content TEXT NOT NULL,
    url TEXT NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (album_id) REFERENCES albums(id)
)
''')
conn_original.commit()

# Transferir album_links
cursor_copia = conn_copia.cursor()
cursor_copia.execute('SELECT album_id, service_name, url FROM album_links')
links = cursor_copia.fetchall()

for link in links:
    try:
        cursor_original.execute('''
        INSERT INTO album_links (album_id, service_name, url) 
        VALUES (?, ?, ?)
        ''', link)
    except sqlite3.IntegrityError:
        print(f"Link ya existente: {link}")

# Transferir album_reviews
cursor_copia.execute('SELECT album_id, source, content, url FROM album_reviews')
reviews = cursor_copia.fetchall()

for review in reviews:
    try:
        cursor_original.execute('''
        INSERT INTO album_reviews (album_id, source, content, url)
        VALUES (?, ?, ?, ?)
        ''', review)
    except sqlite3.IntegrityError:
        print(f"Review ya existente: {review[:50]}...")

# Guardar cambios y cerrar conexiones
conn_original.commit()
conn_copia.close()
conn_original.close()

print("Fusión completada")