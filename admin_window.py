from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt
from database import get_connection
import pandas as pd

class AdminWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Control y Registro - Laboratorio de Ingeniería Inversa & Prototipado - CONCEPTS")
        self.resize(1100, 650)
        
        self.main_layout = QVBoxLayout()
        self.stacked_widget = QStackedWidget()
        
        self.init_ui_menu()
        self.init_ui_usuarios()
        self.init_ui_maquinas()
        
        self.main_layout.addWidget(self.stacked_widget)
        self.setLayout(self.main_layout)
        self.stacked_widget.setCurrentIndex(0)

    # --- PANTALLA 1: MENÚ DE INICIO DEL ADMINISTRADOR ---
    def init_ui_menu(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        
        title = QLabel("Panel de Control Maestro - CONCEPTS")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #1e3d59; margin-bottom: 20px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        btn_ver_usuarios = QPushButton("👥 Ver Usuarios Registrados")
        btn_ver_usuarios.setFixedSize(350, 60)
        btn_ver_usuarios.setStyleSheet("font-size: 16px; background-color: #0d6efd;")
        btn_ver_usuarios.clicked.connect(lambda: [self.load_users_data(), self.stacked_widget.setCurrentIndex(1)])
        layout.addWidget(btn_ver_usuarios)
        
        btn_ver_maquinas = QPushButton("⚙️ Acceder al Registro de Uso de Máquinas")
        btn_ver_maquinas.setFixedSize(350, 60)
        btn_ver_maquinas.setStyleSheet("font-size: 16px; background-color: #198754;")
        btn_ver_maquinas.clicked.connect(lambda: [self.load_master_data(), self.stacked_widget.setCurrentIndex(2)])
        layout.addWidget(btn_ver_maquinas)
        
        btn_logout = QPushButton("🚪 Cerrar Sesión")
        btn_logout.setFixedSize(350, 50)
        btn_logout.setStyleSheet("font-size: 15px; background-color: #dc3545;")
        btn_logout.clicked.connect(self.logout)
        layout.addWidget(btn_logout)
        
        self.stacked_widget.addWidget(page)

    # --- PANTALLA 2: LISTADO DE USUARIOS CON BORRADO ---
    def init_ui_usuarios(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        header = QHBoxLayout()
        title = QLabel("Listado de Cuentas Registradas")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e3d59;")
        header.addWidget(title)
        
        btn_back = QPushButton("🔙 Volver al Menú")
        btn_back.setStyleSheet("max-width: 150px; background-color: #6c757d;")
        btn_back.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        header.addWidget(btn_back)
        layout.addLayout(header)
        
        self.table_users = QTableWidget()
        self.table_users.setColumnCount(5)
        self.table_users.setHorizontalHeaderLabels(["Nombre Completo", "ID Estudiantil", "Usuario", "Teléfono", "Correo"])
        self.table_users.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_users.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table_users)
        
        btn_delete_user = QPushButton("🗑️ Eliminar Cuenta Seleccionada")
        btn_delete_user.setStyleSheet("background-color: #bb2d3b; font-weight: bold; color: white; padding: 10px; font-size: 14px;")
        btn_delete_user.clicked.connect(self.delete_user)
        layout.addWidget(btn_delete_user)
        
        self.stacked_widget.addWidget(page)

    # --- PANTALLA 3: REGISTRO DE USO DE MÁQUINAS ---
    def init_ui_maquinas(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        header = QHBoxLayout()
        title = QLabel("Registro de Uso de Equipos - LIIP")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e3d59;")
        header.addWidget(title)
        
        header.addWidget(QLabel("Filtrar Equipo:"))
        self.cb_filtro_maquina = QComboBox()
        self.cb_filtro_maquina.addItems([
            "Todas las Máquinas",
            "Cortadora láser RisingSun", 
            "Cortadora láser Forza 4", 
            "Impresora 3D FDM K2 Plus", 
            "Impresora 3D Resina Creality Halot", 
            "Impresora 3D Resina Anycubic"
        ])
        self.cb_filtro_maquina.currentTextChanged.connect(self.load_master_data)
        header.addWidget(self.cb_filtro_maquina)
        
        btn_back = QPushButton("🔙 Volver al Menú")
        btn_back.setStyleSheet("max-width: 150px; background-color: #6c757d;")
        btn_back.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        header.addWidget(btn_back)
        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "ID", "Usuario", "Carrera", "Máquina", "Tema", "Inicio", "Fin", "Estado", "Observaciones encargado"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        admin_action_layout = QHBoxLayout()
        self.txt_admin_comment = QLineEdit()
        self.txt_admin_comment.setPlaceholderText("Agregar observación o comentario a la actividad seleccionada...")
        admin_action_layout.addWidget(self.txt_admin_comment)

        btn_approve = QPushButton("✅ Aprobar")
        btn_approve.setStyleSheet("background-color: #198754;")
        btn_approve.clicked.connect(lambda: self.change_status("Aprobada"))
        admin_action_layout.addWidget(btn_approve)

        btn_reject = QPushButton("❌ Rechazar")
        btn_reject.setStyleSheet("background-color: #dc3545;")
        btn_reject.clicked.connect(lambda: self.change_status("Rechazada"))
        admin_action_layout.addWidget(btn_reject)
        layout.addLayout(admin_action_layout)

        reports_layout = QHBoxLayout()
        
        btn_refresh = QPushButton("🔄 Sincronizar Datos")
        btn_refresh.clicked.connect(self.load_master_data)
        reports_layout.addWidget(btn_refresh)

        btn_export_xlsx = QPushButton("📊 Exportar Reporte (.xlsx)")
        btn_export_xlsx.setStyleSheet("background-color: #0f5132; font-weight: bold;")
        btn_export_xlsx.clicked.connect(lambda: self.export_data("xlsx"))
        reports_layout.addWidget(btn_export_xlsx)

        btn_export_csv = QPushButton("📄 Exportar Log (.csv)")
        btn_export_csv.setStyleSheet("background-color: #313131; font-weight: bold;")
        btn_export_csv.clicked.connect(lambda: self.export_data("csv"))
        reports_layout.addWidget(btn_export_csv)

        btn_clear_history = QPushButton("🗑️ Limpiar Historial de Usos")
        btn_clear_history.setStyleSheet("background-color: #bb2d3b; font-weight: bold; color: white;")
        btn_clear_history.clicked.connect(self.clear_history)
        reports_layout.addWidget(btn_clear_history)

        layout.addLayout(reports_layout)
        self.stacked_widget.addWidget(page)

    # --- LÓGICA DE PROCESAMIENTO ---
    def load_users_data(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT nombre_completo, cedula_id, username, telefono, correo FROM usuarios WHERE role = 'user'")
        rows = cursor.fetchall()
        conn.close()

        self.table_users.setRowCount(0)
        for row_idx, row_data in enumerate(rows):
            self.table_users.insertRow(row_idx)
            for col_idx, data in enumerate(row_data):
                self.table_users.setItem(row_idx, col_idx, QTableWidgetItem(str(data)))

    def delete_user(self):
        selected_row = self.table_users.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Atención", "Por favor seleccione un usuario de la lista.")
            return

        username_to_delete = self.table_users.item(selected_row, 2).text()
        nombre_completo = self.table_users.item(selected_row, 0).text()

        if username_to_delete == "admin":
            QMessageBox.critical(self, "Acceso Denegado", "No se puede eliminar la cuenta del Administrador General.")
            return

        reply = QMessageBox.question(
            self, "Confirmar Eliminación", 
            f"¿Está seguro de que desea eliminar permanentemente la cuenta de '{nombre_completo}' ({username_to_delete})?\n"
            "El usuario ya no podrá iniciar sesión.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM usuarios WHERE username = ?", (username_to_delete,))
            conn.commit()
            conn.close()
            
            QMessageBox.information(self, "Cuenta Eliminada", f"La cuenta de {username_to_delete} ha sido borrada con éxito.")
            self.load_users_data()

    def load_master_data(self):
        filtro = self.cb_filtro_maquina.currentText()
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
            
        rows = cursor.fetchall()
        conn.close()

        self.table.setRowCount(0)
        for row_idx, row_data in enumerate(rows):
            self.table.insertRow(row_idx)
            for col_idx, data in enumerate(row_data):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(data)))

    def change_status(self, nuevo_estado):
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Atención", "Por favor seleccione una actividad de la lista.")
            return

        act_id = self.table.item(selected_row, 0).text()
        comentario = self.txt_admin_comment.text().strip()

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE actividades SET estado = ?, comentario_admin = ? WHERE id = ?", (nuevo_estado, comentario, act_id))
        conn.commit()
        conn.close()

        self.txt_admin_comment.clear()
        self.load_master_data()

    def clear_history(self):
        reply = QMessageBox.question(
            self, "Confirmar Eliminación", 
            "¿Está absolutamente seguro de limpiar todo el historial de uso de las máquinas?\nEsta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM actividades")
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Historial Vaciado", "Se han eliminado todos los registros correctamente.")
            self.load_master_data()

    def export_data(self, format_type):
        filtro = self.cb_filtro_maquina.currentText()
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
            QMessageBox.warning(self, "Aviso", f"No existen registros para exportar de: {filtro}.")
            return

        if format_type == "xlsx":
            file_path, _ = QFileDialog.getSaveFileName(self, "Exportar Libro Excel", f"Reporte_{filtro.replace(' ', '_')}", "Excel Files (*.xlsx)")
            if file_path:
                if not file_path.endswith('.xlsx'): file_path += '.xlsx'
                df.to_excel(file_path, index=False)
                QMessageBox.information(self, "Reporte Generado", f"Archivo Excel guardado con éxito.")
        else:
            file_path, _ = QFileDialog.getSaveFileName(self, "Exportar Archivo CSV", f"Reporte_{filtro.replace(' ', '_')}", "CSV Files (*.csv)")
            if file_path:
                if not file_path.endswith('.csv'): file_path += '.csv'
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
                QMessageBox.information(self, "Log Generado", f"Archivo CSV guardado con éxito.")

    def logout(self):
        from login_window import LoginWindow
        self.close()
        self.login = LoginWindow()
        self.login.show()