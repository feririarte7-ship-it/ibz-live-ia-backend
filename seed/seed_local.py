import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "sql" / "ibiza_local.db"

def crear_tabla():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            club TEXT,
            artista TEXT,
            nombre TEXT,
            precio_min INTEGER,
            precio_max INTEGER,
            dia_semana INTEGER,
            fecha TEXT
        )
    ''')
    conn.commit()
    conn.close()

def insertar_eventos():
    eventos = [
        ('ushuaia', 'Dom Dolla', 'Dom Dolla & Friends', 60, 140, 0, None),
        ('ushuaia', 'Black Coffee', 'Black Coffee & Friends', 65, 150, 5, None),
        ('pacha', 'Sonny Fodera', 'Sonny Fodera & Friends', 45, 120, 0, None),
        ('pacha', 'Solomun', 'Solomun +1', 60, 140, 6, None),
        ('unvrs', 'John Summit', 'Experts Only', 70, 180, 0, None),
        ('unvrs', 'Anyma', 'ÆDEN', 80, 200, 1, None),
        ('amnesia', 'Sven Väth', 'Cocoon', 55, 130, 1, None),
    ]
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executemany('''
        INSERT INTO eventos (club, artista, nombre, precio_min, precio_max, dia_semana, fecha)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', eventos)
    conn.commit()
    conn.close()
    print("✅ Eventos insertados correctamente")

if __name__ == "__main__":
    crear_tabla()
    insertar_eventos()
