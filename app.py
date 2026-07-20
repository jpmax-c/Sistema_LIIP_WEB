from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
from database import get_connection, hash_password, initialize_database
from datetime import datetime
import pandas as pd
import io
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from flask import send_from_directory, abort

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
            
            # Redirección según el rol correspondiente[cite: 4]
            if role == 'admin':
                return redirect(url_for('admin_menu'))
            elif role == 'tecnico':
                return redirect(url_for('tecnico_panel'))
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
            # Por defecto se registran como estudiantes ('user')[cite: 4]
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
# 3. ÁREA DE USUARIO / ESTUDIANTE (UserWindow)
# ----------------------------------------------------
@app.route('/user_panel')
def user_panel():
    if 'username' not in session or session.get('role') != 'user':
        return redirect(url_for('login'))
    
    username = session['username']
    conn = get_connection()
    cursor = conn.cursor()
    
    # Prácticas en ejecución en máquinas físicas[cite: 4]
    cursor.execute("""
        SELECT id, maquina, tema, fecha_inicio, num_personas 
        FROM actividades 
        WHERE usuario = ? AND estado = 'En ejecución'
    """, (username,))
    actividades = cursor.fetchall()
    
    # Historial de solicitudes enviadas al laboratorio para revisión del Técnico
    cursor.execute("""
        SELECT id, codigo_solicitud, nombre_proyecto, tipo_servicio, material_solicitado, estado, fecha_ingreso
        FROM solicitudes 
        WHERE usuario = ? 
        ORDER BY id DESC
    """, (username,))
    solicitudes = cursor.fetchall()
    
    conn.close()
    
    return render_template('user_panel.html', username=username, actividades=actividades, solicitudes=solicitudes)


# ----------------------------------------------------
# 4. FORMULARIO DE SOLICITUDES / ACTIVIDADES (Para el Técnico)
# ----------------------------------------------------
@app.route('/solicitudes/nueva', methods=['GET', 'POST'])
def nueva_solicitud():
    if 'username' not in session or session.get('role') != 'user':
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        usuario = session['username']
        nombre_proyecto = request.form.get('nombre_proyecto', '').strip()
        archivo_ruta = request.form.get('archivo_ruta', '').strip()
        tipo_servicio = request.form.get('tipo_servicio')
        material_solicitado = request.form.get('material_solicitado', '').strip()
        cantidad = int(request.form.get('cantidad', 1))
        prioridad = request.form.get('prioridad', 'Normal')
        fecha_ingreso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Generación de código único
        codigo_solicitud = f"REQ-{datetime.now().year}-{random.randint(1000, 9999)}"

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO solicitudes (codigo_solicitud, usuario, nombre_proyecto, archivo_ruta, tipo_servicio, material_solicitado, cantidad, prioridad, fecha_ingreso)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (codigo_solicitud, usuario, nombre_proyecto, archivo_ruta, tipo_servicio, material_solicitado, cantidad, prioridad, fecha_ingreso))
            conn.commit()
            flash("¡Actividad registrada y enviada al Técnico de laboratorio!", "success")
        except Exception as e:
            flash(f"Error al registrar: {str(e)}", "danger")
        finally:
            conn.close()
            
        return redirect(url_for('user_panel'))

    return render_template('nueva_solicitud.html')


# ----------------------------------------------------
# 5. FORMULARIO DE PRÁCTICAS (PracticeFormWindow)
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
            fecha_inicio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO actividades (usuario, maquina, num_personas, tema, observaciones, fecha_inicio)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (username, maquina, personas, tema, observaciones, fecha_inicio))
            flash("¡Práctica iniciada con éxito!", "success")
        else:
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
# 6. ÁREA DE TÉCNICO DE LABORATORIO
# ----------------------------------------------------
@app.route('/tecnico_panel')
def tecnico_panel():
    if 'username' not in session or session.get('role') != 'tecnico':
        return redirect(url_for('login'))
        
    conn = get_connection()
    cursor = conn.cursor()
    # Muestra todas las actividades de los alumnos
    cursor.execute("""
        SELECT s.id, s.codigo_solicitud, u.nombre_completo, s.nombre_proyecto, 
               s.tipo_servicio, s.material_solicitado, s.estado, s.fecha_ingreso
        FROM solicitudes s
        INNER JOIN usuarios u ON s.usuario = u.username
        ORDER BY s.id DESC
    """)
    solicitudes = cursor.fetchall()
    conn.close()
    
    return render_template('tecnico_panel.html', solicitudes=solicitudes)


@app.route('/tecnico/actualizar_estado', methods=['POST'])
def tecnico_actualizar_estado():
    if 'username' not in session or session.get('role') != 'tecnico':
        return redirect(url_for('login'))
        
    solicitud_id = request.form.get('solicitud_id')
    nuevo_estado = request.form.get('nuevo_estado')
    comentario = request.form.get('comentario_personal', '').strip()
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE solicitudes 
        SET estado = ?, comentario_personal = ? 
        WHERE id = ?
    """, (nuevo_estado, comentario, solicitud_id))
    conn.commit()
    conn.close()
    
    flash(f"Actividad #{solicitud_id} actualizada correctamente.", "success")
    return redirect(url_for('tecnico_panel'))


# ----------------------------------------------------
# 7. ÁREA DE ADMINISTRACIÓN (AdminWindow)
# ----------------------------------------------------
@app.route('/admin')
def admin_menu():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    return render_template('admin_menu.html')


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


# ----------------------------------------------------
# 8. EXPORTACIÓN E IMPORTACIÓN A EXCEL
# ----------------------------------------------------
@app.route('/admin/export/<format_type>')
def export_data(format_type):
    if 'username' not in session or session.get('role') not in ['admin', 'tecnico']:
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
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Registros")
        output.seek(0)
        return Response(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment;filename={filename}.xlsx"}
        )
    else:
        csv_data = df.to_csv(index=False, encoding='utf-8-sig')
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename={filename}.csv"}
        )


@app.route('/admin/importar/usuarios', methods=['POST'])
def importar_usuarios_excel():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    file = request.files.get('archivo_excel')
    if not file or file.filename == '':
        flash("No seleccionó ningún archivo.", "warning")
        return redirect(url_for('admin_users'))

    if not file.filename.endswith(('.xlsx', '.xls')):
        flash("Formato inválido. Debe subir un archivo Excel (.xlsx).", "danger")
        return redirect(url_for('admin_users'))

    try:
        df = pd.read_excel(file)
        columnas_requeridas = ['username', 'password', 'nombre_completo', 'cedula_id', 'carrera_departamento', 'telefono', 'correo', 'role']
        if not all(col in df.columns for col in columnas_requeridas):
            flash("El Excel no cuenta con la estructura o cabeceras requeridas.", "danger")
            return redirect(url_for('admin_users'))

        # Detectar el marcador dinámico de base de datos
        from database import DATABASE_URL
        conn = get_connection()
        cursor = conn.cursor()
        param_style = "%s" if DATABASE_URL else "?"
        
        usuarios_creados = 0
        for _, row in df.iterrows():
            pass_encriptada = hash_password(str(row['password']))
            try:
                cursor.execute(f"""
                    INSERT INTO usuarios (username, password, nombre_completo, cedula_id, carrera_departamento, telefono, correo, role)
                    VALUES ({param_style}, {param_style}, {param_style}, {param_style}, {param_style}, {param_style}, {param_style}, {param_style})
                """, (
                    str(row['username']).strip(),
                    pass_encriptada,
                    str(row['nombre_completo']).strip(),
                    str(row['cedula_id']).strip(),
                    str(row['carrera_departamento']).strip(),
                    str(row['telefono']).strip(),
                    str(row['correo']).strip(),
                    str(row['role']).strip().lower()
                ))
                usuarios_creados += 1
            except Exception:
                continue # Salta duplicados de llave única
                
        conn.commit()
        conn.close()
        flash(f"Carga finalizada. Se registraron {usuarios_creados} usuarios desde el Excel.", "success")
        
    except Exception as e:
        flash(f"Error procesando el documento: {str(e)}", "danger")

    return redirect(url_for('admin_users'))

# CONFIGURACIÓN SMTP (Reemplaza con tus credenciales reales o variables de entorno)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "pjallauca@espe.edu.ec"  # Tu correo institucional completo
SMTP_PASSWORD = "tavsboavbchhvqxt" # Las 16 letras que debes generar

def enviar_correo_codigo(correo_destino, codigo):
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = correo_destino
        msg['Subject'] = "Código de Recuperación - Laboratorio CONCEPTS"

        cuerpo = f"""
        <html>
        <body>
            <h2>Recuperación de Contraseña</h2>
            <p>Has solicitado restablecer tu contraseña para el sistema del Laboratorio de Ingeniería Inversa y Prototipado CONCEPTS.</p>
            <p>Tu código de verificación temporal es:</p>
            <h1 style='color: #007bff;'>{codigo}</h1>
            <p>Este código vencerá al cerrar la ventana de recuperación.</p>
        </body>
        </html>
        """
        msg.attach(MIMEText(cuerpo, 'html'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, correo_destino, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error enviando correo: {e}")
        return False

# RUTA: Solicitar Código
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT correo FROM usuarios WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()

        if result and result[0]:
            correo = result[0]
            codigo = str(random.randint(100000, 999999))
            session['recovery_code'] = codigo
            session['recovery_user'] = username
            
            if enviar_correo_codigo(correo, codigo):
                flash(f"Se ha enviado un código de verificación al correo asociado: {correo[:3]}***{correo[correo.find('@'):]}", "info")
                return redirect(url_for('verify_code'))
            else:
                flash("Error al enviar el correo. Por favor, contacta al administrador.", "danger")
        else:
            flash("El usuario ingresado no existe o no cuenta con un correo registrado.", "warning")

    return render_template('forgot_password.html')

# RUTA: Verificar Código
@app.route('/verify_code', methods=['GET', 'POST'])
def verify_code():
    if 'recovery_user' not in session or 'recovery_code' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        codigo_ingresado = request.form.get('codigo', '').strip()

        if codigo_ingresado == session.get('recovery_code'):
            session['code_verified'] = True
            return redirect(url_for('reset_password'))
        else:
            flash("El código de verificación es incorrecto.", "danger")

    return render_template('verify_code.html')

# RUTA: Restablecer Contraseña
@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if not session.get('code_verified'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        nueva_pass = request.form.get('password', '').strip()
        confirm_pass = request.form.get('confirm_password', '').strip()

        if nueva_pass != confirm_pass:
            flash("Las contraseñas no coinciden.", "warning")
            return redirect(url_for('reset_password'))

        username = session.get('recovery_user')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        from database import DATABASE_URL
        param_style = "%s" if DATABASE_URL else "?"
        
        cursor.execute(f"UPDATE usuarios SET password = {param_style} WHERE username = {param_style}", (hash_password(nueva_pass), username))
        conn.commit()
        conn.close()

        session.clear()
        flash("Contraseña actualizada con éxito. Ya puedes iniciar sesión.", "success")
        return redirect(url_for('login'))

    return render_template('reset_password.html')

# Define la carpeta donde se guardan los archivos subidos (si no la tienes arriba)
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/uploads/<filename>')
def download_file(filename):
    try:
        # Envía de forma segura el archivo desde el directorio de subidas al navegador
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except FileNotFoundError:
        abort(404)

if __name__ == '__main__':
    app.run(debug=True)