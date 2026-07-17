from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
from database import get_connection, hash_password, initialize_database
from datetime import datetime
import pandas as pd
import io

app = Flask(__name__)
app.secret_key = "CONCEPTS_SECRET_KEY_PROTOTIPADO" # Cambia por una clave segura en producción

# Inicializar Base de Datos en el arranque
initialize_database()

# ----------------------------------------------------
# 1. AUTENTICACIÓN (LoginWindow)
# ----------------------------------------------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash("Por favor, ingrese su usuario y contraseña.", "warning")
            return redirect(url_for('login'))

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM usuarios WHERE username = ? AND password = ?", (username, hash_password(password)))
        result = cursor.fetchone()
        conn.close()

        if result:
            role = result[0]
            session['username'] = username
            session['role'] = role
            if role == 'admin':
                return redirect(url_for('admin_menu'))
            else:
                return redirect(url_for('user_panel'))
        else:
            flash("El usuario o la contraseña son incorrectos.", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ----------------------------------------------------
# 2. REGISTRO DE USUARIOS (RegisterWindow)
# ----------------------------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        cedula = request.form.get('cedula', '').strip()
        carrera = request.form.get('carrera', '').strip()
        telefono = request.form.get('telefono', '').strip()
        correo = request.form.get('correo', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not all([nombre, cedula, carrera, telefono, correo, username, password]):
            flash("Todos los datos personales son obligatorios.", "warning")
            return redirect(url_for('register'))

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO usuarios (username, password, nombre_completo, cedula_id, carrera_departamento, telefono, correo, role) 
                VALUES (?, ?, ?, ?, ?, ?, ?, 'user')
            """, (username, hash_password(password), nombre, cedula, carrera, telefono, correo))
            conn.commit()
            flash("Cuenta registrada con éxito. Ya puedes iniciar sesión.", "success")
            return redirect(url_for('login'))
        except Exception:
            flash("El nombre de usuario ya se encuentra registrado.", "danger")
            return redirect(url_for('register'))
        finally:
            conn.close()

    return render_template('register.html')


# ----------------------------------------------------
# 3. ÁREA DE USUARIO (UserWindow)
# ----------------------------------------------------
@app.route('/user_panel')
def user_panel():
    if 'username' not in session or session.get('role') != 'user':
        return redirect(url_for('login'))
    
    username = session['username']
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, maquina, tema, fecha_inicio, num_personas 
        FROM actividades 
        WHERE usuario = ? AND estado = 'En ejecución'
    """, (username,))
    actividades = cursor.fetchall()
    conn.close()
    
    return render_template('user_panel.html', username=username, actividades=actividades)


# ----------------------------------------------------
# 4. FORMULARIO DE PRÁCTICAS (PracticeFormWindow)
# ----------------------------------------------------
@app.route('/practice/new', methods=['GET', 'POST'])
@app.route('/practice/edit/<int:actividad_id>', methods=['GET', 'POST'])
def practice_form(actividad_id=None):
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    maquinas = [
        "Cortadora láser RisingSun", 
        "Cortadora láser Forza 4", 
        "Impresora 3D FDM K2 Plus", 
        "Impresora 3D Resina Creality Halot", 
        "Impresora 3D Resina Anycubic"
    ]
    
    # Cargar datos si es modo edición
    actividad = None
    if actividad_id:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, maquina, num_personas, tema, observaciones FROM actividades WHERE id = ?", (actividad_id,))
        actividad = cursor.fetchone()
        conn.close()

    if request.method == 'POST':
        maquina = request.form.get('maquina')
        personas = int(request.form.get('personas'))
        tema = request.form.get('tema', '').strip()
        observaciones = request.form.get('observaciones', '').strip()

        if not tema:
            flash("El campo 'Tema / Ensayo' es obligatorio.", "warning")
            return redirect(request.url)

        conn = get_connection()
        cursor = conn.cursor()

        if actividad_id is None:
            # Insertar nueva actividad
            fecha_inicio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO actividades (usuario, maquina, num_personas, tema, observaciones, fecha_inicio)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (username, maquina, personas, tema, observaciones, fecha_inicio))
            flash("¡Práctica iniciada con éxito!", "success")
        else:
            # Guardar edición
            cursor.execute("""
                UPDATE actividades 
                SET maquina = ?, num_personas = ?, tema = ?, observaciones = ? 
                WHERE id = ?
            """, (maquina, personas, tema, observaciones, actividad_id))
            flash("Práctica modificada con éxito.", "success")

        conn.commit()
        conn.close()
        return redirect(url_for('user_panel'))

    return render_template('practice_form.html', maquinas=maquinas, actividad=actividad)


@app.route('/practice/finish/<int:actividad_id>')
def finish_practice(actividad_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    fecha_fin = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE actividades 
        SET fecha_fin = ?, estado = 'Finalizada' 
        WHERE id = ?
    """, (fecha_fin, actividad_id))
    conn.commit()
    conn.close()
    
    flash("La práctica ha sido marcada como Finalizada con éxito.", "success")
    return redirect(url_for('user_panel'))


# ----------------------------------------------------
# 5. ÁREA DE ADMINISTRACIÓN (AdminWindow)
# ----------------------------------------------------
@app.route('/admin')
def admin_menu():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    return render_template('admin_menu.html')


# PANTALLA 2: Control de Cuentas de Usuarios
@app.route('/admin/users')
def admin_users():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre_completo, cedula_id, username, telefono, correo FROM usuarios WHERE role = 'user'")
    usuarios = cursor.fetchall()
    conn.close()
    return render_template('admin_users.html', usuarios=usuarios)


@app.route('/admin/users/delete/<username_to_delete>', methods=['POST'])
def delete_user(username_to_delete):
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    if username_to_delete == "admin":
        flash("No se puede eliminar la cuenta del Administrador General.", "danger")
        return redirect(url_for('admin_users'))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE username = ?", (username_to_delete,))
    conn.commit()
    conn.close()
    
    flash(f"La cuenta de '{username_to_delete}' ha sido borrada con éxito.", "success")
    return redirect(url_for('admin_users'))


# PANTALLA 3: Registro de Uso de Máquinas
@app.route('/admin/machines', methods=['GET', 'POST'])
def admin_machines():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    maquinas_filtro = [
        "Todas las Máquinas",
        "Cortadora láser RisingSun", 
        "Cortadora láser Forza 4", 
        "Impresora 3D FDM K2 Plus", 
        "Impresora 3D Resina Creality Halot", 
        "Impresora 3D Resina Anycubic"
    ]

    filtro = request.args.get('filtro', 'Todas las Máquinas')

    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT a.id, u.nombre_completo, u.carrera_departamento, a.maquina, a.tema, a.fecha_inicio, a.fecha_fin, a.estado, a.comentario_admin 
        FROM actividades a
        INNER JOIN usuarios u ON a.usuario = u.username
    """
    if filtro != "Todas las Máquinas":
        query += " WHERE a.maquina = ?"
        query += " ORDER BY a.id DESC"
        cursor.execute(query, (filtro,))
    else:
        query += " ORDER BY a.id DESC"
        cursor.execute(query)
        
    actividades = cursor.fetchall()
    conn.close()

    return render_template('admin_machines.html', actividades=actividades, filtros=maquinas_filtro, filtro_actual=filtro)


@app.route('/admin/machines/status', methods=['POST'])
def change_status():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    act_id = request.form.get('act_id')
    nuevo_estado = request.form.get('nuevo_estado')
    comentario = request.form.get('comentario_admin', '').strip()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE actividades SET estado = ?, comentario_admin = ? WHERE id = ?", (nuevo_estado, comentario, act_id))
    conn.commit()
    conn.close()

    flash(f"Actividad #{act_id} marcada como '{nuevo_estado}' con éxito.", "success")
    return redirect(url_for('admin_machines', filtro=request.form.get('filtro_actual')))


@app.route('/admin/machines/clear', methods=['POST'])
def clear_history():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM actividades")
    conn.commit()
    conn.close()

    flash("Se ha vaciado todo el historial de usos correctamente.", "success")
    return redirect(url_for('admin_machines'))


# EXPORTACIÓN DE REPORTES (Excel/CSV de pandas)
@app.route('/admin/export/<format_type>')
def export_data(format_type):
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    filtro = request.args.get('filtro', 'Todas las Máquinas')
    conn = get_connection()
    
    query = """
        SELECT a.id AS ID_Actividad, u.nombre_completo AS Operador, u.cedula_id AS Identificacion, 
               u.carrera_departamento AS Area, a.maquina AS Maquina_Utilizada, a.num_personas AS Cantidad_Personas,
               a.tema AS Proyecto_Ensayo, a.observaciones AS Notas_Operador, a.fecha_inicio AS Tiempo_Inicio, 
               a.fecha_fin AS Tiempo_Fin, a.estado AS Estado_Validacion, a.comentario_admin AS Comentarios_Administracion
        FROM actividades a
        INNER JOIN usuarios u ON a.usuario = u.username
    """
    if filtro != "Todas las Máquinas":
        query += " WHERE a.maquina = '" + filtro + "'"
        
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        flash(f"No existen registros para exportar de: {filtro}.", "warning")
        return redirect(url_for('admin_machines', filtro=filtro))

    output = io.BytesIO()
    filename = f"Reporte_{filtro.replace(' ', '_')}"

    if format_type == "xlsx":
        # Exportación de Pandas a Memoria (Sin guardar localmente en el servidor)
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Registros")
        output.seek(0)
        return Response(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment;filename={filename}.xlsx"}
        )
    else:
        # Exportación CSV UTF-8 con soporte para tildes (BOM)
        csv_data = df.to_csv(index=False, encoding='utf-8-sig')
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename={filename}.csv"}
        )


if __name__ == '__main__':
    app.run(debug=True)