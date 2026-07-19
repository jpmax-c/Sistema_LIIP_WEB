import sqlite3
import os
import hashlib
import urllib.parse as urlparse

# Intentar obtener la base de datos de producción (Render)
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_connection():
    if DATABASE_URL:
        import psycopg2
        url = urlparse.urlparse(DATABASE_URL)
        return psycopg2.connect(
            dbname=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
        )
    else:
        DB_FOLDER = "data"
        DB_PATH = os.path.join(DB_FOLDER, "laboratorio.db")
        os.makedirs(DB_FOLDER, exist_ok=True)
        return sqlite3.connect(DB_PATH)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()
    
    param_style = "%s" if DATABASE_URL else "?"

    # 1. Tabla de Usuarios
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        nombre_completo TEXT NOT NULL,
        cedula_id TEXT NOT NULL,
        carrera_departamento TEXT NOT NULL,
        telefono TEXT DEFAULT '',
        correo TEXT DEFAULT '',
        role TEXT NOT NULL CHECK(role IN ('admin', 'tecnico', 'user'))
    )
    """)
    
    # 2. Tabla de Actividades de Prototipado
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS actividades (
        id SERIAL PRIMARY KEY,
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

    # 3. Tabla de Solicitudes/Actividades enviadas al Técnico
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS solicitudes (
        id SERIAL PRIMARY KEY,
        codigo_solicitud TEXT UNIQUE NOT NULL,
        usuario TEXT NOT NULL,
        nombre_proyecto TEXT NOT NULL,
        archivo_ruta TEXT NOT NULL,
        tipo_servicio TEXT NOT NULL,
        material_solicitado TEXT NOT NULL,
        cantidad INTEGER NOT NULL DEFAULT 1,
        prioridad TEXT NOT NULL DEFAULT 'Normal',
        estado TEXT NOT NULL DEFAULT 'Pendiente',
        tiempo_estimado INTEGER NOT NULL DEFAULT 0,
        fecha_ingreso TEXT NOT NULL,
        fecha_inicio TEXT DEFAULT NULL,
        fecha_fin TEXT DEFAULT NULL,
        equipo_asignado_id INTEGER DEFAULT NULL,
        comentario_personal TEXT DEFAULT ''
    )
    """)
    
    # Administrador por defecto
    cursor.execute(f"SELECT * FROM usuarios WHERE username = {param_style}", ("admin",))
    if not cursor.fetchone():
        cursor.execute(f"""
            INSERT INTO usuarios (username, password, nombre_completo, cedula_id, carrera_departamento, telefono, correo, role) 
            VALUES ({param_style}, {param_style}, {param_style}, {param_style}, {param_style}, {param_style}, {param_style}, {param_style})
        """, ("admin", hash_password("admin123"), "Administrador General", "0000000000", "LIIP", "0000000000", "admin@liip.com", "admin"))
        
    conn.commit()
    conn.close()