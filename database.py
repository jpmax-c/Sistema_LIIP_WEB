import sqlite3
import os
import hashlib

DB_FOLDER = "data"
DB_PATH = os.path.join(DB_FOLDER, "laboratorio.db")
os.makedirs(DB_FOLDER, exist_ok=True)

def get_connection():
    return sqlite3.connect(DB_PATH)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabla de Usuarios
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        nombre_completo TEXT NOT NULL,
        cedula_id TEXT NOT NULL,
        carrera_departamento TEXT NOT NULL,
        telefono TEXT NOT NULL DEFAULT '',
        correo TEXT NOT NULL DEFAULT '',
        role TEXT NOT NULL CHECK(role IN ('admin', 'user'))
    )
    """)
    
    # Tabla de Actividades de Prototipado
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS actividades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT NOT NULL,
        maquina TEXT NOT NULL,
        num_personas INTEGER NOT NULL,
        tema TEXT NOT NULL,
        observaciones TEXT,
        comentario_admin TEXT DEFAULT '',
        fecha_inicio TEXT NOT NULL,
        fecha_fin TEXT DEFAULT 'En ejecución',
        estado TEXT DEFAULT 'En ejecución'
    )
    """)
    
    # Administrador por defecto
    cursor.execute("SELECT * FROM usuarios WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO usuarios (username, password, nombre_completo, cedula_id, carrera_departamento, telefono, correo, role) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ("admin", hash_password("admin123"), "Administrador General", "0000000000", "Laboratorio", "0000000000", "admin@concepts.com", "admin"))
        
    conn.commit()
    conn.close()