import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import queue
import time
import datetime
import os
import csv
from collections import deque
import scipy.signal as signal
from PIL import Image, ImageTk

# Verificar pyrtools como dependencia obligatoria
try:
    import pyrtools as pt
except ImportError:
    import sys
    print("ERROR: pyrtools es una dependencia obligatoria para Motion Magnification GUI")
    print("Instálalo con: pip install pyrtools")
    print("O ejecuta: python launcher.py para instalación automática")
    sys.exit(1)

from skimage import img_as_float, img_as_ubyte
import copy

class MotionMagnificationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Motion Magnification - Sistema de Monitoreo de Vibraciones")
        self.root.geometry("1400x900")  # Ventana más grande para el nuevo layout
        self.root.minsize(1200, 700)    # Tamaño mínimo
        
        # Variables de control
        self.camera = None
        self.is_running = False
        self.selected_camera = tk.IntVar(value=0)
        self.fps = tk.DoubleVar(value=10.0)
        self.alpha = tk.DoubleVar(value=200.0)
        self.lambda_c = tk.DoubleVar(value=120.0)
        self.fl = tk.DoubleVar(value=0.07)
        self.fh = tk.DoubleVar(value=3.0)
        
        # Variables para calibración física
        self.mm_per_pixel = tk.DoubleVar(value=0.1)  # mm por píxel (calibrar)
        self.is_calibrated = False
        self.calibration_distance_mm = tk.DoubleVar(value=10.0)  # distancia conocida en mm
        self.calibration_pixels = tk.IntVar(value=100)  # píxeles correspondientes
        
        # Queue para comunicación entre threads
        self.message_queue = queue.Queue()
        self.data_queue = queue.Queue()
        self.video_queue = queue.Queue()
        
        # Buffer para datos
        self.signal_buffer = deque(maxlen=300)
        self.frame_count = 0
        
        # Variables para grabación CSV
        self.is_recording = False
        self.csv_file = None
        self.csv_writer = None
        self.recording_filename = ""
        
        # Variables para ROI
        self.roi = None
        self.magnify_engine = None
        
        # Variables para calibración de ruido de fondo
        self.noise_calibration_active = False  # Indica si está en modo calibración de ruido
        self.noise_calibration_frames = []  # Frames capturados durante la calibración
        self.noise_calibration_model = None  # Modelo de ruido de fondo calibrado
        self.noise_calibration_count = 0  # Contador de frames durante calibración
        self.noise_calibration_duration = tk.IntVar(value=5)  # Segundos para calibrar
        self.use_noise_calibration = tk.BooleanVar(value=False)  # Activar/desactivar uso del modelo
        
        # --- Variables para filtrado de ruido en video ---
        # Nivel de reducción de ruido (controlado por el usuario)
        self.noise_reduction_level = tk.DoubleVar(value=2.0)
        # Activar/desactivar sustracción de fondo (checkbox en la GUI)
        self.background_subtraction = tk.BooleanVar(value=False)
        # Activar/desactivar filtrado morfológico (checkbox en la GUI)
        self.morphological_filtering = tk.BooleanVar(value=True)
        # Activar/desactivar suavizado temporal (checkbox en la GUI)
        self.temporal_smoothing = tk.BooleanVar(value=True)
        # Modelo de fondo para sustracción (se captura automáticamente)
        self.background_model = None
        # Buffer de frames para suavizado temporal
        self.frame_buffer = deque(maxlen=5)
        
        # Variables para video display
        self.current_frame = None
        
        self.setup_ui()
        self.update_console()
        # Iniciar actualización de video con delay
        self.root.after(1000, self.update_video_display)
        
    def setup_ui(self):
        """Configurar la interfaz de usuario con pestañas"""
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # --- Pestaña 1: Configuración y consola ---
        config_console_tab = ttk.Frame(notebook)
        notebook.add(config_console_tab, text="Configuración y Consola")

        # Frame superior para controles/configuración
        control_frame = ttk.Frame(config_console_tab)
        control_frame.pack(fill='x', padx=5, pady=(5, 0))
        self.setup_control_panel(control_frame)

        # Frame inferior para consola
        console_frame = ttk.Frame(config_console_tab)
        console_frame.pack(fill='both', expand=True, padx=5, pady=5)
        self.setup_console_panel(console_frame)

        # --- Pestaña 2: Video y gráficas ---
        video_graph_tab = ttk.Frame(notebook)
        notebook.add(video_graph_tab, text="Video y Gráficas")

        # Crear un PanedWindow horizontal para dividir video y gráficas
        h_paned = ttk.PanedWindow(video_graph_tab, orient=tk.HORIZONTAL)
        h_paned.pack(fill='both', expand=True, padx=5, pady=5)

        # Frame izquierdo para video
        video_frame = ttk.Frame(h_paned)
        h_paned.add(video_frame, weight=1)
        self.setup_video_panel(video_frame)

        # Frame derecho para gráficas
        graph_frame = ttk.Frame(h_paned)
        h_paned.add(graph_frame, weight=2)
        self.setup_graph_panel(graph_frame)
        
    def setup_control_panel(self, parent):
        """Configurar el panel de control"""
        # Frame superior para configuración
        config_frame = ttk.LabelFrame(parent, text="Configuración de Parámetros")
        config_frame.pack(fill='x', padx=5, pady=5)
        
        # Selección de cámara
        ttk.Label(config_frame, text="Cámara:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        camera_combo = ttk.Combobox(config_frame, textvariable=self.selected_camera, 
                                   values=list(range(5)), state='readonly', width=8)
        camera_combo.grid(row=0, column=1, padx=5, pady=2)
        
        # FPS
        ttk.Label(config_frame, text="FPS:").grid(row=0, column=2, sticky='w', padx=5, pady=2)
        fps_spinbox = ttk.Spinbox(config_frame, from_=1, to=60, textvariable=self.fps, 
                                 width=8, increment=1)
        fps_spinbox.grid(row=0, column=3, padx=5, pady=2)
        
        # Alpha
        ttk.Label(config_frame, text="Alpha:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        alpha_spinbox = ttk.Spinbox(config_frame, from_=1, to=1000, textvariable=self.alpha, 
                                   width=8, increment=10)
        alpha_spinbox.grid(row=1, column=1, padx=5, pady=2)
        
        # Lambda_c
        ttk.Label(config_frame, text="Lambda_c:").grid(row=1, column=2, sticky='w', padx=5, pady=2)
        lambda_spinbox = ttk.Spinbox(config_frame, from_=1, to=500, textvariable=self.lambda_c, 
                                    width=8, increment=10)
        lambda_spinbox.grid(row=1, column=3, padx=5, pady=2)
        
        # Frecuencias
        ttk.Label(config_frame, text="fl:").grid(row=2, column=0, sticky='w', padx=5, pady=2)
        fl_spinbox = ttk.Spinbox(config_frame, from_=0.01, to=10, textvariable=self.fl, 
                                width=8, increment=0.01, format="%.3f")
        fl_spinbox.grid(row=2, column=1, padx=5, pady=2)
        
        ttk.Label(config_frame, text="fh:").grid(row=2, column=2, sticky='w', padx=5, pady=2)
        fh_spinbox = ttk.Spinbox(config_frame, from_=0.1, to=20, textvariable=self.fh, 
                                width=8, increment=0.1, format="%.2f")
        fh_spinbox.grid(row=2, column=3, padx=5, pady=2)
        
        # Calibración física
        calib_separator = ttk.Separator(config_frame, orient='horizontal')
        calib_separator.grid(row=3, column=0, columnspan=4, sticky='ew', pady=5)
        
        ttk.Label(config_frame, text="📏 Calibración Física", font=('Arial', 9, 'bold')).grid(
            row=4, column=0, columnspan=4, pady=2)
        
        ttk.Label(config_frame, text="Dist. real (mm):").grid(row=5, column=0, sticky='w', padx=5, pady=2)
        calib_dist_spinbox = ttk.Spinbox(config_frame, from_=1, to=1000, textvariable=self.calibration_distance_mm, 
                                        width=8, increment=1, format="%.1f")
        calib_dist_spinbox.grid(row=5, column=1, padx=5, pady=2)
        
        ttk.Label(config_frame, text="Píxeles:").grid(row=5, column=2, sticky='w', padx=5, pady=2)
        calib_pixels_spinbox = ttk.Spinbox(config_frame, from_=1, to=5000, textvariable=self.calibration_pixels, 
                                          width=8, increment=1)
        calib_pixels_spinbox.grid(row=5, column=3, padx=5, pady=2)
        
        # Sección de calibración de ruido
        noise_calib_frame = ttk.LabelFrame(parent, text="Calibración de Ruido de Fondo")
        noise_calib_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(noise_calib_frame, text="⚠️ Para usar esta función, la máquina debe estar APAGADA", 
                  font=('Arial', 8, 'italic'), foreground="red").pack(pady=2)
        
        calib_controls = ttk.Frame(noise_calib_frame)
        calib_controls.pack(pady=5)
        
        ttk.Label(calib_controls, text="Duración (seg):").pack(side='left', padx=5)
        duration_spinbox = ttk.Spinbox(calib_controls, from_=2, to=30, 
                                    textvariable=self.noise_calibration_duration,
                                    width=5, increment=1)
        duration_spinbox.pack(side='left', padx=5)
        
        use_calib_check = ttk.Checkbutton(calib_controls, text="Usar calibración", 
                                         variable=self.use_noise_calibration)
        use_calib_check.pack(side='left', padx=20)
        
        calib_buttons = ttk.Frame(noise_calib_frame)
        calib_buttons.pack(pady=5)
        
        self.calibrate_noise_button = ttk.Button(calib_buttons, text="🔧 Calibrar Ruido", 
                                              command=self.start_noise_calibration)
        self.calibrate_noise_button.pack(side='left', padx=5)
        
        self.noise_calib_status = ttk.Label(calib_buttons, text="No calibrado", foreground="orange")
        self.noise_calib_status.pack(side='left', padx=5)
        
        # Botones de control
        button_frame = ttk.LabelFrame(parent, text="Controles de Monitoreo")
        button_frame.pack(fill='x', padx=5, pady=5)
        
        # Primera fila de botones
        button_row1 = ttk.Frame(button_frame)
        button_row1.pack(pady=5)
        
        self.start_button = ttk.Button(button_row1, text="▶ Iniciar", command=self.start_monitoring)
        self.start_button.pack(side='left', padx=5)
        
        self.start_no_calib_button = ttk.Button(button_row1, text="▶ Iniciar Sin Calibración", 
                                              command=lambda: self.start_monitoring(use_calibration=False))
        self.start_no_calib_button.pack(side='left', padx=5)
        
        self.stop_button = ttk.Button(button_row1, text="⏹ Detener", command=self.stop_monitoring, 
                                     state='disabled')
        self.stop_button.pack(side='left', padx=5)
        
        # Segunda fila de botones
        button_row2 = ttk.Frame(button_frame)
        button_row2.pack(pady=5)
        
        self.roi_button = ttk.Button(button_row2, text="🎯 Seleccionar ROI", 
                                    command=self.select_roi, state='disabled')
        self.roi_button.pack(side='left', padx=5)
        
        self.auto_tune_button = ttk.Button(button_row2, text="⚙️ Auto-tune", 
                                          command=self.auto_tune_frequencies, state='disabled')
        self.auto_tune_button.pack(side='left', padx=5)
        
        # Tercera fila de botones para calibración
        button_row3 = ttk.Frame(button_frame)
        button_row3.pack(pady=5)
        
        self.calibrate_button = ttk.Button(button_row3, text="📏 Calibrar", 
                                          command=self.calibrate_physical_scale, state='disabled')
        self.calibrate_button.pack(side='left', padx=5)
        
        self.measure_button = ttk.Button(button_row3, text="📐 Medir", 
                                        command=self.measure_distance, state='disabled')
        self.measure_button.pack(side='left', padx=5)
        
        # Cuarta fila de botones para grabación
        button_row4 = ttk.Frame(button_frame)
        button_row4.pack(pady=5)
        
        self.record_button = ttk.Button(button_row4, text="🔴 Iniciar Grabación", 
                                       command=self.start_recording, state='disabled')
        self.record_button.pack(side='left', padx=5)
        
        self.stop_record_button = ttk.Button(button_row4, text="⏺ Detener Grabación", 
                                            command=self.stop_recording, state='disabled')
        self.stop_record_button.pack(side='left', padx=5)
        
        # Frame para mostrar estado actual
        status_frame = ttk.LabelFrame(parent, text="Estado del Sistema")
        status_frame.pack(fill='x', padx=5, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="Sistema detenido", foreground="red")
        self.status_label.pack(pady=5)
        
        # Variables de estado para mostrar
        self.roi_status_label = ttk.Label(status_frame, text="ROI: No seleccionado", foreground="orange")
        self.roi_status_label.pack(pady=2)
        
        self.calibration_status_label = ttk.Label(status_frame, text="Calibración: No calibrado", foreground="red")
        self.calibration_status_label.pack(pady=2)
        
        self.recording_status_label = ttk.Label(status_frame, text="Grabación: Detenida", foreground="orange")
        self.recording_status_label.pack(pady=2)
        
    def setup_video_panel(self, parent):
        """Configurar el panel de video"""
        video_frame = ttk.LabelFrame(parent, text="Video en Tiempo Real con ROI")
        video_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Status frame for video filters
        video_status_frame = ttk.Frame(video_frame)
        video_status_frame.pack(fill='x', padx=5, pady=2)
        
        self.noise_filter_status_label = ttk.Label(video_status_frame, text="Filtros: Desactivados", foreground="orange")
        self.noise_filter_status_label.pack(pady=2)
        
        # Crear un frame con scroll si es necesario
        self.video_label = ttk.Label(video_frame, text="📹 El video aparecerá aquí cuando inicies el monitoreo", 
                                    font=('Arial', 12), foreground="gray")
        self.video_label.pack(expand=True)
        
    def setup_graph_panel(self, parent):
        """Configurar el panel de gráficas"""
        graph_label_frame = ttk.LabelFrame(parent, text="Análisis en Tiempo Real")
        graph_label_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Frame para gráficas con mejor layout
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(8, 6))
        self.fig.patch.set_facecolor('white')
        
        # Gráfica de señal de vibración
        self.ax1.set_title("📊 Señal de Vibración (ROI)", fontsize=12, fontweight='bold')
        self.ax1.set_xlabel("Frame #")
        self.ax1.set_ylabel("Intensidad Media")
        self.ax1.grid(True, alpha=0.3)
        self.line1, = self.ax1.plot([], [], 'b-', linewidth=1.5, label='Señal de vibración')
        self.ax1.legend(loc='upper right')
        
        # Gráfica FFT - la etiqueta del eje Y se actualizará dinámicamente
        self.ax2.set_title("📈 Espectro de Frecuencias (FFT)", fontsize=12, fontweight='bold')
        self.ax2.set_xlabel("Frecuencia (Hz)")
        self.ax2.set_ylabel("Magnitud")  # Se actualizará dinámicamente
        self.ax2.grid(True, alpha=0.3)
        self.line2, = self.ax2.plot([], [], 'r-', linewidth=1.5, label='FFT')
        self.ax2.legend(loc='upper right')
        
        plt.tight_layout()
        
        # Integrar matplotlib en tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, graph_label_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill='both', expand=True, padx=5, pady=5)
        
    def setup_console_panel(self, parent):
        """Configurar el panel de consola"""
        console_label_frame = ttk.LabelFrame(parent, text="📝 Consola del Sistema")
        console_label_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Frame para botones de consola
        console_buttons = ttk.Frame(console_label_frame)
        console_buttons.pack(fill='x', padx=5, pady=2)
        
        # Botón para limpiar consola
        clear_button = ttk.Button(console_buttons, text="🗑️ Limpiar", 
                                 command=self.clear_console)
        clear_button.pack(side='left', padx=5)
        
        # Área de texto para consola con altura reducida
        self.console_text = scrolledtext.ScrolledText(console_label_frame, height=8, width=60,
                                                     font=('Courier', 9))
        self.console_text.pack(fill='both', expand=True, padx=5, pady=5)
        
    def setup_graph_tab(self, parent):
        """MÉTODO DEPRECADO - Reemplazado por setup_graph_panel"""
        # Mantenido por compatibilidad, no se usa
        pass
        
    def setup_console_tab(self, parent):
        """MÉTODO DEPRECADO - Reemplazado por setup_console_panel"""  
        # Mantenido por compatibilidad, no se usa
        pass
        
    def log_message(self, message):
        """Agregar mensaje a la cola para mostrar en consola"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.message_queue.put(f"[{timestamp}] {message}")
        
    def update_console(self):
        """Actualizar la consola con mensajes de la cola"""
        try:
            while True:
                message = self.message_queue.get_nowait()
                self.console_text.insert(tk.END, message + "\n")
                self.console_text.see(tk.END)
        except queue.Empty:
            pass
        
        # Programar siguiente actualización solo si la ventana está activa
        if self.root.winfo_exists():
            self.root.after(100, self.update_console)
        
    def clear_console(self):
        """Limpiar el área de consola"""
        self.console_text.delete(1.0, tk.END)
        
    def update_video_display(self):
        """Actualizar la visualización del video"""
        try:
            while True:
                frame = self.video_queue.get_nowait()
                
                # Redimensionar frame para la GUI (máximo 500x400 para el nuevo layout)
                height, width = frame.shape[:2]
                max_width, max_height = 500, 400
                
                if width > max_width or height > max_height:
                    scale = min(max_width/width, max_height/height)
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    frame = cv2.resize(frame, (new_width, new_height))
                
                # Convertir de BGR a RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Convertir a PIL Image y luego a PhotoImage
                pil_image = Image.fromarray(frame_rgb)
                photo = ImageTk.PhotoImage(pil_image)
                
                # Actualizar el label del video
                self.video_label.configure(image=photo, text="")
                self.video_label.image = photo  # Mantener referencia
                
        except queue.Empty:
            pass
        except Exception as e:
            self.log_message(f"Error actualizando video: {str(e)}")
        
        # Programar siguiente actualización solo si la ventana está activa
        if self.root.winfo_exists():
            self.root.after(50, self.update_video_display)  # 20 FPS para la GUI
        
    def start_monitoring(self, use_calibration=True):
        """Iniciar el monitoreo de vibración"""
        try:
            # Inicializar cámara
            camera_id = self.selected_camera.get()
            self.camera = cv2.VideoCapture(camera_id)
            
            if not self.camera.isOpened():
                messagebox.showerror("Error", f"No se pudo abrir la cámara {camera_id}")
                return
                
            # Establecer si se usa calibración de ruido
            if not use_calibration:
                self.use_noise_calibration.set(False)
                self.log_message("Iniciando sin calibración de ruido de fondo")
                
            self.log_message(f"Cámara {camera_id} inicializada correctamente")
            
            # Actualizar estado visual
            self.status_label.config(text="Sistema ejecutándose", foreground="green")
            
            # Cambiar estado de botones
            self.start_button.config(state='disabled')
            self.start_no_calib_button.config(state='disabled')
            self.stop_button.config(state='normal')
            self.roi_button.config(state='normal')
            self.auto_tune_button.config(state='normal')
            self.calibrate_button.config(state='normal')
            self.measure_button.config(state='normal')
            self.record_button.config(state='normal')
            self.calibrate_noise_button.config(state='disabled')
            
            self.is_running = True
            
            # Update noise filter status display
            self.update_noise_filter_status()
            
            # Iniciar thread de procesamiento
            self.processing_thread = threading.Thread(target=self.processing_loop)
            self.processing_thread.daemon = True
            self.processing_thread.start()
            
            # Iniciar actualización de gráficas
            self.update_graphs()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al iniciar: {str(e)}")
            self.log_message(f"Error al iniciar: {str(e)}")
            
    def stop_monitoring(self):
        """Detener el monitoreo"""
        self.is_running = False
        
        # Detener grabación si está activa
        if self.is_recording:
            self.stop_recording()
        
        if self.camera:
            self.camera.release()
            
        cv2.destroyAllWindows()
        
        # Actualizar estado visual
        self.status_label.config(text="Sistema detenido", foreground="red")
        self.roi_status_label.config(text="ROI: No seleccionado", foreground="orange")
        if not self.is_calibrated:
            self.calibration_status_label.config(text="Calibración: No calibrado", foreground="red")
        
        # Cambiar estado de botones
        self.start_button.config(state='normal')
        self.start_no_calib_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.roi_button.config(state='disabled')
        self.auto_tune_button.config(state='disabled')
        self.calibrate_button.config(state='disabled')
        self.measure_button.config(state='disabled')
        self.record_button.config(state='disabled')
        self.stop_record_button.config(state='disabled')
        self.calibrate_noise_button.config(state='normal')
        
        # Limpiar video display
        self.video_label.config(image="", text="📹 El video aparecerá aquí cuando inicies el monitoreo")
        
        self.log_message("Monitoreo detenido")
        
    def select_roi(self):
        """Seleccionar ROI en la imagen"""
        if not self.camera:
            return
            
        ret, frame = self.camera.read()
        if not ret:
            messagebox.showerror("Error", "No se pudo leer de la cámara")
            return
            
        # Mostrar ventana para seleccionar ROI
        self.roi = cv2.selectROI("Selecciona ROI", frame, fromCenter=False, showCrosshair=True)
        cv2.destroyWindow("Selecciona ROI")
        
        if self.roi[2] > 0 and self.roi[3] > 0:
            x, y, w, h = self.roi
            self.log_message(f"ROI seleccionado: x={x}, y={y}, ancho={w}, alto={h}")
            self.roi_status_label.config(text=f"ROI: {w}x{h} en ({x},{y})", foreground="green")
            
            # Inicializar motor de magnificación
            roi_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)[y:y+h, x:x+w]
            roi_gray = cv2.GaussianBlur(roi_gray, (5, 5), 0)
            
            self.magnify_engine = Magnify(roi_gray, 
                                        self.alpha.get(), 
                                        self.lambda_c.get(), 
                                        self.fl.get(), 
                                        self.fh.get(), 
                                        self.fps.get())
                                        
            self.log_message("Motor de magnificación inicializado")
        else:
            self.log_message("ROI no válido seleccionado")
            self.roi_status_label.config(text="ROI: Selección cancelada", foreground="red")
            
    def auto_tune_frequencies(self):
        """Auto-ajustar frecuencias fl y fh"""
        if not self.camera or not self.roi:
            messagebox.showwarning("Advertencia", "Primero selecciona un ROI")
            return
            
        self.log_message("Iniciando auto-ajuste de frecuencias...")
        
        # Recolectar señal para análisis
        buffer_size = min(100, int(self.fps.get() * 5))
        auto_buffer = []
        x, y, w, h = self.roi
        
        for i in range(buffer_size):
            ret, frame = self.camera.read()
            if not ret:
                break
                
            roi_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)[y:y+h, x:x+w]
            roi_gray = cv2.GaussianBlur(roi_gray, (5, 5), 0)
            mean_signal = np.mean(roi_gray)
            auto_buffer.append(mean_signal)
            
            if i % 10 == 0:
                self.log_message(f"Recolectando... {i}/{buffer_size}")
                
        # Calcular fl y fh automáticamente
        fl, fh = self.auto_tune_fl_fh(auto_buffer, self.fps.get())
        
        # Actualizar variables
        self.fl.set(fl)
        self.fh.set(fh)
        
        self.log_message(f"Auto-ajuste completado: fl={fl:.3f}, fh={fh:.3f}")
        
    def calibrate_physical_scale(self):
        """Calibrar la escala física usando una distancia conocida"""
        if not self.camera:
            messagebox.showwarning("Advertencia", "Primero inicia el monitoreo")
            return
            
        ret, frame = self.camera.read()
        if not ret:
            messagebox.showerror("Error", "No se pudo leer de la cámara")
            return
        
        messagebox.showinfo("Calibración", 
                           f"Selecciona dos puntos que estén separados {self.calibration_distance_mm.get()}mm")
        
        # Variables para almacenar los puntos de calibración
        self.calib_points = []
        self.calib_frame = frame.copy()
        
        # Crear ventana para calibración
        cv2.namedWindow("Calibración - Haz clic en dos puntos", cv2.WINDOW_NORMAL)
        cv2.setMouseCallback("Calibración - Haz clic en dos puntos", self.calibration_mouse_callback)
        
        while len(self.calib_points) < 2:
            display_frame = self.calib_frame.copy()
            
            # Dibujar puntos ya seleccionados
            for i, point in enumerate(self.calib_points):
                cv2.circle(display_frame, point, 5, (0, 255, 0), -1)
                cv2.putText(display_frame, f"P{i+1}", (point[0]+10, point[1]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Mostrar instrucciones
            if len(self.calib_points) == 0:
                cv2.putText(display_frame, "Haz clic en el primer punto", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            elif len(self.calib_points) == 1:
                cv2.putText(display_frame, "Haz clic en el segundo punto", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            cv2.imshow("Calibración - Haz clic en dos puntos", display_frame)
            
            if cv2.waitKey(1) & 0xFF == 27:  # ESC para cancelar
                break
                
        cv2.destroyWindow("Calibración - Haz clic en dos puntos")
        
        if len(self.calib_points) == 2:
            # Calcular distancia en píxeles
            p1, p2 = self.calib_points
            pixel_distance = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
            
            # Calcular mm por píxel
            mm_per_pixel = self.calibration_distance_mm.get() / pixel_distance
            self.mm_per_pixel.set(mm_per_pixel)
            self.is_calibrated = True
            
            self.log_message(f"Calibración completada: {mm_per_pixel:.4f} mm/píxel")
            self.log_message(f"Distancia medida: {pixel_distance:.1f} píxeles = {self.calibration_distance_mm.get()}mm")
            self.calibration_status_label.config(
                text=f"Calibración: {mm_per_pixel:.4f} mm/px", foreground="green")
        else:
            self.log_message("Calibración cancelada")
            
    def calibration_mouse_callback(self, event, x, y, flags, param):
        """Callback para capturar clics durante la calibración"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.calib_points.append((x, y))
            
    def measure_distance(self):
        """Herramienta para medir distancias usando la calibración"""
        if not self.is_calibrated:
            messagebox.showwarning("Advertencia", "Primero calibra la escala física")
            return
            
        if not self.camera:
            return
            
        ret, frame = self.camera.read()
        if not ret:
            return
        
        # Variables para almacenar los puntos de medición
        self.measure_points = []
        self.measure_frame = frame.copy()
        
        messagebox.showinfo("Medición", "Selecciona dos puntos para medir la distancia")
        
        cv2.namedWindow("Medición - Haz clic en dos puntos", cv2.WINDOW_NORMAL)
        cv2.setMouseCallback("Medición - Haz clic en dos puntos", self.measure_mouse_callback)
        
        while len(self.measure_points) < 2:
            display_frame = self.measure_frame.copy()
            
            # Dibujar puntos y línea
            for i, point in enumerate(self.measure_points):
                cv2.circle(display_frame, point, 5, (255, 0, 0), -1)
                cv2.putText(display_frame, f"M{i+1}", (point[0]+10, point[1]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            
            if len(self.measure_points) == 2:
                cv2.line(display_frame, self.measure_points[0], self.measure_points[1], (255, 0, 0), 2)
                
            # Mostrar instrucciones
            if len(self.measure_points) == 0:
                cv2.putText(display_frame, "Haz clic en el primer punto", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            elif len(self.measure_points) == 1:
                cv2.putText(display_frame, "Haz clic en el segundo punto", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            cv2.imshow("Medición - Haz clic en dos puntos", display_frame)
            
            if cv2.waitKey(1) & 0xFF == 27:  # ESC para cancelar
                break
                
        cv2.destroyWindow("Medición - Haz clic en dos puntos")
        
        if len(self.measure_points) == 2:
            # Calcular distancia
            p1, p2 = self.measure_points
            pixel_distance = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
            mm_distance = pixel_distance * self.mm_per_pixel.get()
            
            messagebox.showinfo("Resultado de Medición", 
                              f"Distancia medida:\n{pixel_distance:.1f} píxeles\n{mm_distance:.2f} mm")
            self.log_message(f"Medición: {pixel_distance:.1f}px = {mm_distance:.2f}mm")
        else:
            self.log_message("Medición cancelada")
            
    def measure_mouse_callback(self, event, x, y, flags, param):
        """Callback para capturar clics durante la medición"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.measure_points.append((x, y))
            
    def start_noise_calibration(self):
        """
        Inicia el proceso de calibración de ruido de fondo.
        Captura varios frames de la máquina apagada para crear un modelo de referencia.
        """
        if not self.camera:
            try:
                # Inicializar cámara temporalmente para calibración
                camera_id = self.selected_camera.get()
                self.camera = cv2.VideoCapture(camera_id)
                if not self.camera.isOpened():
                    messagebox.showerror("Error", f"No se pudo abrir la cámara {camera_id}")
                    return
                self.log_message("Cámara inicializada para calibración de ruido")
                temporary_camera = True
            except Exception as e:
                messagebox.showerror("Error", f"Error al inicializar cámara: {str(e)}")
                return
        else:
            temporary_camera = False
            
        try:
            # Resetear variables de calibración
            self.noise_calibration_active = True
            self.noise_calibration_frames = []
            self.noise_calibration_count = 0
            duration = self.noise_calibration_duration.get()
            total_frames = int(duration * self.fps.get())
            
            # Actualizar interfaz
            self.calibrate_noise_button.config(state='disabled')
            self.noise_calib_status.config(text=f"Calibrando... 0%", foreground="blue")
            self.log_message(f"Iniciando calibración de ruido por {duration} segundos...")
            
            # Iniciar proceso de captura
            self.capture_noise_frames(temporary_camera, total_frames)
            
        except Exception as e:
            self.noise_calibration_active = False
            if temporary_camera and self.camera:
                self.camera.release()
                self.camera = None
            messagebox.showerror("Error", f"Error al iniciar calibración de ruido: {str(e)}")
            self.log_message(f"Error en calibración de ruido: {str(e)}")
            
    def capture_noise_frames(self, temporary_camera, total_frames):
        """Capturar frames para calibración de ruido de fondo"""
        if not self.camera or not self.noise_calibration_active:
            return
            
        try:
            # Capturar un frame
            ret, frame = self.camera.read()
            if ret:
                # Guardar frame en escala de grises
                gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                self.noise_calibration_frames.append(gray_frame)
                self.noise_calibration_count += 1
                
                # Actualizar progreso
                progress = (self.noise_calibration_count / total_frames) * 100
                self.noise_calib_status.config(text=f"Calibrando... {progress:.0f}%", foreground="blue")
                
                # Mostrar vista previa
                height, width = frame.shape[:2]
                max_width, max_height = 500, 400
                if width > max_width or height > max_height:
                    scale = min(max_width/width, max_height/height)
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    frame = cv2.resize(frame, (new_width, new_height))
                
                # Añadir texto indicando que es calibración de ruido
                cv2.putText(frame, "CALIBRANDO RUIDO", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.7, (0, 0, 255), 2)
                cv2.putText(frame, f"Frame {self.noise_calibration_count}/{total_frames}", (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                
                # Actualizar vista previa
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(frame_rgb)
                photo = ImageTk.PhotoImage(pil_image)
                self.video_label.configure(image=photo, text="")
                self.video_label.image = photo
            
            # Verificar si hemos terminado
            if self.noise_calibration_count < total_frames:
                # Programar siguiente captura
                self.root.after(int(1000 / self.fps.get()), 
                               lambda: self.capture_noise_frames(temporary_camera, total_frames))
            else:
                # Hemos terminado de capturar frames
                self.complete_noise_calibration(temporary_camera)
        except Exception as e:
            self.log_message(f"Error capturando frames de ruido: {str(e)}")
            self.noise_calibration_active = False
            if temporary_camera and self.camera:
                self.camera.release()
                self.camera = None
                
    def complete_noise_calibration(self, temporary_camera):
        """Finalizar proceso de calibración de ruido creando el modelo"""
        try:
            if len(self.noise_calibration_frames) > 0:
                # Crear modelo promediando todos los frames
                self.log_message(f"Procesando {len(self.noise_calibration_frames)} frames para modelo de ruido...")
                
                # Convertir a array numpy para operaciones eficientes
                frames_array = np.array(self.noise_calibration_frames)
                
                # Calcular media y desviación estándar por pixel
                mean_frame = np.mean(frames_array, axis=0)
                std_frame = np.std(frames_array, axis=0)
                
                # Guardar modelo como diccionario
                self.noise_calibration_model = {
                    'mean': mean_frame,
                    'std': std_frame,
                    'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'frames_used': len(self.noise_calibration_frames)
                }
                
                # Actualizar interfaz
                self.noise_calib_status.config(
                    text=f"Calibrado ({len(self.noise_calibration_frames)} frames)", 
                    foreground="green")
                
                # Activar uso de calibración por defecto
                self.use_noise_calibration.set(True)
                
                # Mensaje de éxito
                self.log_message("Calibración de ruido completada con éxito.")
                messagebox.showinfo("Calibración de Ruido", 
                                  "Modelo de ruido calibrado con éxito.\n"\
                                  "Ahora puedes iniciar el monitoreo con la máquina ENCENDIDA.")
            else:
                self.noise_calib_status.config(text="Error: No hay frames", foreground="red")
                self.log_message("Error: No se capturaron frames para calibración de ruido")
        except Exception as e:
            self.log_message(f"Error procesando modelo de ruido: {str(e)}")
            self.noise_calib_status.config(text="Error en calibración", foreground="red")
            
        finally:
            # Limpiar variables temporales
            self.noise_calibration_active = False
            self.noise_calibration_frames = []
            self.calibrate_noise_button.config(state='normal')
            
            # Cerrar cámara si fue abierta temporalmente
            if temporary_camera and self.camera:
                self.camera.release()
                self.camera = None
                # Restaurar mensaje de video
                self.video_label.config(image="", text="📹 El video aparecerá aquí cuando inicies el monitoreo")
                
    def apply_noise_calibration(self, frame):
        """
        Aplica el modelo de calibración de ruido al frame actual.
        Reduce el ruido estático detectado durante la calibración.
        """
        if not self.use_noise_calibration.get() or self.noise_calibration_model is None:
            return frame
        try:
            # Convertir a escala de grises y a float32
            if len(frame.shape) == 3:
                gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
            else:
                gray_frame = frame.astype(np.float32)

            # Obtener modelo calibrado y convertir a float32
            mean_noise = self.noise_calibration_model['mean'].astype(np.float32)
            std_noise = self.noise_calibration_model['std'].astype(np.float32)

            # Verificar dimensiones
            if gray_frame.shape != mean_noise.shape:
                mean_noise = cv2.resize(mean_noise, (gray_frame.shape[1], gray_frame.shape[0]))
                std_noise = cv2.resize(std_noise, (gray_frame.shape[1], gray_frame.shape[0]))

            # Restar ruido medio
            clean_frame = gray_frame - mean_noise

            # Aplicar umbral adaptativo basado en la desviación estándar
            threshold = std_noise * 2
            mask = np.where(np.abs(clean_frame) < threshold, 0, 255).astype(np.uint8)

            # Si el frame original es a color, aplicar la máscara a cada canal
            if len(frame.shape) == 3:
                result = frame.copy()
                for c in range(frame.shape[2]):
                    result[:, :, c] = cv2.bitwise_and(result[:, :, c], mask)
                return result
            else:
                # Convertir de vuelta a uint8 para visualización
                return cv2.bitwise_and(gray_frame.astype(np.uint8), mask)
        except Exception as e:
            self.log_message(f"Error aplicando modelo de ruido: {str(e)}")
            return frame
            
    def toggle_background_subtraction(self):
        """
        Alterna la sustracción de fondo. Si se activa, el modelo de fondo se capturará automáticamente
        en el loop de procesamiento tras unos frames. Si se desactiva, se borra el modelo.
        """
        if self.background_subtraction.get() and self.is_running:
            self.log_message("Activando sustracción de fondo - capturando modelo...")
            # El modelo se capturará en el processing_loop
        elif not self.background_subtraction.get():
            self.background_model = None
            self.log_message("Sustracción de fondo desactivada")
            
    def apply_noise_filtering(self, frame, roi_region=None):
        """
        Aplica una serie de filtros de reducción de ruido al frame de video:
        0. Calibración de ruido (elimina ruido consistente si está calibrado)
        1. Filtro Gaussiano adaptativo (reduce ruido general)
        2. Sustracción de fondo (elimina fondo estático si está activado)
        3. Filtrado morfológico (elimina ruido tipo sal y pimienta)
        4. Suavizado temporal (reduce parpadeo y ruido temporal)
        Si roi_region se pasa, la máscara de fondo se aplica solo al ROI.
        """
        filtered_frame = frame.copy()
        
        # --- 0. Aplicar modelo de calibración de ruido si está activo ---
        if self.use_noise_calibration.get() and self.noise_calibration_model is not None:
            filtered_frame = self.apply_noise_calibration(filtered_frame)
        
        # --- 1. Filtrado Gaussiano adaptativo ---
        noise_level = self.noise_reduction_level.get()
        kernel_size = max(3, int(noise_level * 2) + 1)  # Tamaño de kernel adaptativo
        if kernel_size % 2 == 0:
            kernel_size += 1
        filtered_frame = cv2.GaussianBlur(filtered_frame, (kernel_size, kernel_size), noise_level)
        # --- 2. Sustracción de fondo ---
        if self.background_subtraction.get() and self.background_model is not None:
            # Convertir a escala de grises si es necesario
            gray_frame = cv2.cvtColor(filtered_frame, cv2.COLOR_BGR2GRAY) if len(filtered_frame.shape) == 3 else filtered_frame
            gray_bg = cv2.cvtColor(self.background_model, cv2.COLOR_BGR2GRAY) if len(self.background_model.shape) == 3 else self.background_model
            # Diferencia absoluta entre frame y fondo
            diff = cv2.absdiff(gray_frame, gray_bg)
            # Umbralización adaptativa para eliminar fondo
            threshold_value = np.mean(diff) + noise_level * np.std(diff)
            _, mask = cv2.threshold(diff, threshold_value, 255, cv2.THRESH_BINARY)
            # Si se pasa un ROI, aplicar la máscara solo a esa región
            if roi_region is not None and len(roi_region.shape) == 3:
                roi_gray = cv2.cvtColor(roi_region, cv2.COLOR_BGR2GRAY)
                roi_mask = cv2.resize(mask, (roi_region.shape[1], roi_region.shape[0]))
                # Aplicar máscara solo a la región de interés (canal por canal)
                for c in range(roi_region.shape[2]):
                    roi_region[:, :, c] = cv2.bitwise_and(roi_region[:, :, c], roi_mask)
        # --- 3. Filtrado morfológico ---
        if self.morphological_filtering.get():
            # Kernel pequeño para operaciones morfológicas
            kernel = np.ones((3, 3), np.uint8)
            if len(filtered_frame.shape) == 3:  # Frame a color
                for c in range(filtered_frame.shape[2]):
                    # Opening (erosión+dilatación) y closing (dilatación+erosión)
                    filtered_frame[:, :, c] = cv2.morphologyEx(filtered_frame[:, :, c], cv2.MORPH_OPEN, kernel)
                    filtered_frame[:, :, c] = cv2.morphologyEx(filtered_frame[:, :, c], cv2.MORPH_CLOSE, kernel)
            else:  # Frame en escala de grises
                filtered_frame = cv2.morphologyEx(filtered_frame, cv2.MORPH_OPEN, kernel)
                filtered_frame = cv2.morphologyEx(filtered_frame, cv2.MORPH_CLOSE, kernel)
        # --- 4. Suavizado temporal ---
        if self.temporal_smoothing.get() and len(self.frame_buffer) > 0:
            # Promediar con el frame anterior para reducir ruido temporal
            alpha = 0.7  # Factor de mezcla
            if len(self.frame_buffer) > 0:
                previous_frame = self.frame_buffer[-1]
                if previous_frame.shape == filtered_frame.shape:
                    filtered_frame = cv2.addWeighted(filtered_frame, alpha, previous_frame, 1-alpha, 0)
        # Añadir frame actual al buffer temporal
        self.frame_buffer.append(filtered_frame.copy())
        return filtered_frame
        
    def apply_roi_noise_filtering(self, roi_gray):
        """
        Aplica filtros adicionales al ROI (región de interés) en escala de grises:
        1. Filtro bilateral: preserva bordes y reduce ruido
        2. Filtro de mediana: elimina ruido impulsivo
        3. Filtro gaussiano suave si la varianza es alta (tipo Wiener)
        """
        filtered_roi = roi_gray.copy()
        noise_level = self.noise_reduction_level.get()
        # --- 1. Filtro bilateral ---
        d = int(noise_level * 3)  # Diámetro del filtro
        sigma_color = noise_level * 20
        sigma_space = noise_level * 20
        filtered_roi = cv2.bilateralFilter(filtered_roi, d, sigma_color, sigma_space)
        # --- 2. Filtro de mediana ---
        kernel_size = max(3, int(noise_level))
        if kernel_size % 2 == 0:
            kernel_size += 1
        filtered_roi = cv2.medianBlur(filtered_roi, kernel_size)
        # --- 3. Filtro gaussiano si la varianza es alta ---
        laplacian_var = cv2.Laplacian(filtered_roi, cv2.CV_64F).var()
        noise_var = noise_level * 10
        if laplacian_var > noise_var:
            filtered_roi = cv2.GaussianBlur(filtered_roi, (3, 3), 0.8)
        return filtered_roi
        
    def update_noise_filter_status(self):
        """Actualizar el estado visual de los filtros de ruido"""
        active_filters = []
        
        # Mostrar si se está usando la calibración de ruido
        if self.use_noise_calibration.get() and self.noise_calibration_model is not None:
            active_filters.append("NoiseCalib✓")
        
        if self.background_subtraction.get():
            bg_status = "BG✓" if self.background_model is not None else "BG⏳"
            active_filters.append(bg_status)
            
        if self.morphological_filtering.get():
            active_filters.append("Morph✓")
            
        if self.temporal_smoothing.get():
            active_filters.append("Temp✓")
            
        if active_filters:
            filter_text = f"Filtros activos: {', '.join(active_filters)} (Nivel: {self.noise_reduction_level.get():.1f})"
            self.noise_filter_status_label.config(text=filter_text, foreground="green")
        else:
            self.noise_filter_status_label.config(text="Filtros: Desactivados", foreground="orange")
            

    def start_recording(self):
        """Iniciar la grabación de datos al archivo CSV"""
        if not self.is_running:
            messagebox.showwarning("Advertencia", "Primero inicia el monitoreo del sistema")
            return
            
        try:
            # Crear archivo CSV para grabación
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.recording_filename = f"historiales/vibration_recording_{timestamp}.csv"
            
            # Asegurar que el directorio existe
            os.makedirs("historiales", exist_ok=True)
            
            # Abrir archivo para escritura
            self.csv_file = open(self.recording_filename, mode='w', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            
            # Escribir headers según el estado de calibración
            if self.is_calibrated:
                self.csv_writer.writerow(["frame", "timestamp", "mean_magnitude_px_frame", 
                                        "velocity_mm_s", "mean_signal", "mm_per_pixel"])
            else:
                self.csv_writer.writerow(["frame", "timestamp", "mean_magnitude_px_frame", "mean_signal"])
            
            self.is_recording = True
            
            # Actualizar interfaz
            self.record_button.config(state='disabled')
            self.stop_record_button.config(state='normal')
            self.recording_status_label.config(text=f"Grabación: ACTIVA - {self.recording_filename}", 
                                             foreground="green")
            
            self.log_message(f"Grabación iniciada: {self.recording_filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al iniciar grabación: {str(e)}")
            self.log_message(f"Error al iniciar grabación: {str(e)}")
            
    def stop_recording(self):
        """Detener la grabación de datos"""
        if not self.is_recording:
            return
            
        try:
            # Cerrar archivo CSV
            if self.csv_file:
                self.csv_file.close()
                self.csv_file = None
                self.csv_writer = None
            
            self.is_recording = False
            
            # Actualizar interfaz
            self.record_button.config(state='normal' if self.is_running else 'disabled')
            self.stop_record_button.config(state='disabled')
            self.recording_status_label.config(text="Grabación: Detenida", foreground="orange")
            
            self.log_message(f"Grabación detenida. Archivo guardado: {self.recording_filename}")
            
            # Solo mostrar messagebox si el sistema está ejecutándose (evitar popup al cerrar)
            if self.is_running:
                messagebox.showinfo("Grabación", f"Datos guardados en:\n{self.recording_filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al detener grabación: {str(e)}")
            self.log_message(f"Error al detener grabación: {str(e)}")
        
    def convert_to_physical_units(self, magnitude_px_per_frame):
        """Convertir magnitud de píxeles/frame a unidades físicas"""
        if not self.is_calibrated:
            return magnitude_px_per_frame, "px/frame"
            
        # Convertir a mm/frame
        mm_per_frame = magnitude_px_per_frame * self.mm_per_pixel.get()
        
        # Convertir a mm/s
        time_per_frame = 1.0 / self.fps.get()  # segundos por frame
        mm_per_second = mm_per_frame / time_per_frame
        
        return mm_per_second, "mm/s"
        
    def auto_tune_fl_fh(self, signal_buffer, fps):
        """Ajustar automáticamente fl y fh usando picos del espectro"""
        from scipy.signal import find_peaks
        
        signal_arr = np.array(signal_buffer) - np.mean(signal_buffer)
        fft_vals = np.abs(np.fft.rfft(signal_arr))
        freqs = np.fft.rfftfreq(len(signal_arr), d=1.0/fps)
        
        peaks, _ = find_peaks(fft_vals[1:], height=np.max(fft_vals[1:]) * 0.2)
        peaks = peaks + 1  # ignorar DC
        
        if len(peaks) > 0:
            fl = max(0.01, freqs[peaks].min() - 0.2)
            fh = freqs[peaks].max() + 0.2
        else:
            peak_idx = np.argmax(fft_vals[1:]) + 1
            dominant_freq = freqs[peak_idx]
            fl = max(0.01, dominant_freq - 0.5)
            fh = dominant_freq + 0.5
            
        return fl, fh
        
    def processing_loop(self):
        """Loop principal de procesamiento"""
        self.log_message("Iniciando loop de procesamiento...")
        
        # Crear archivo CSV para historial
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"historiales/vibration_history_{timestamp}.csv"
        
        os.makedirs("historiales", exist_ok=True)
        
        with open(csv_filename, mode='w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
            # Agregar headers para unidades físicas
            if self.is_calibrated:
                csv_writer.writerow(["frame", "timestamp", "mean_magnitude_px_frame", 
                                   "velocity_mm_s", "mean_signal", "mm_per_pixel"])
            else:
                csv_writer.writerow(["frame", "timestamp", "mean_magnitude_px_frame", "mean_signal"])
            
            prev_gray = None
            
            while self.is_running:
                try:
                    ret, frame = self.camera.read()
                    if not ret:
                        break
                        
                    self.frame_count += 1
                    
                    # Procesar solo si hay ROI y motor de magnificación
                    if self.roi and self.magnify_engine:
                        x, y, w, h = self.roi
                        roi_img = frame[y:y+h, x:x+w]
                        
                        # Magnificación
                        gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
                        out = self.magnify_engine.Magnify(gray)
                        
                        # Flujo óptico si hay frame previo
                        mean_magnitude = 0
                        if prev_gray is not None:
                            flow = cv2.calcOpticalFlowFarneback(prev_gray, out, None, 
                                                              0.5, 3, 15, 3, 5, 1.2, 0)
                            mean_magnitude = np.mean(cv2.norm(flow, cv2.NORM_L2))
                            
                        prev_gray = out.copy()
                        
                        # Mostrar resultado magnificado en frame original
                        frame[y:y+h, x:x+w] = cv2.cvtColor(out, cv2.COLOR_GRAY2BGR)
                        
                        # Dibujar rectángulo del ROI con información
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 3)
                        
                        # Convertir a unidades físicas si está calibrado
                        physical_value, physical_units = self.convert_to_physical_units(mean_magnitude)
                        
                        # Mostrar información del ROI y magnitud
                        if self.is_calibrated:
                            info_text = f"ROI: {w}x{h} | Velocidad: {physical_value:.2f} {physical_units}"
                        else:
                            info_text = f"ROI: {w}x{h} | Magnitud: {mean_magnitude:.2f} px/frame"
                        
                        cv2.putText(frame, info_text, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 
                                   0.6, (0, 255, 0), 2)
                        
                        # Mostrar parámetros actuales
                        params_text = f"Alpha: {self.alpha.get():.0f} | fl: {self.fl.get():.3f}Hz | fh: {self.fh.get():.2f}Hz"
                        cv2.putText(frame, params_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                                   0.5, (255, 255, 255), 1)
                        
                        # Datos para gráficas
                        mean_signal = np.mean(out)
                        self.signal_buffer.append(mean_signal)
                        
                        # Guardar en CSV automático para historial
                        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        if self.is_calibrated:
                            physical_value, _ = self.convert_to_physical_units(mean_magnitude)
                            csv_writer.writerow([self.frame_count, timestamp_str, 
                                               mean_magnitude, physical_value, mean_signal, 
                                               self.mm_per_pixel.get()])
                        else:
                            csv_writer.writerow([self.frame_count, timestamp_str, 
                                               mean_magnitude, mean_signal])
                        
                        # Guardar en CSV de grabación si está activa
                        if self.is_recording and self.csv_writer:
                            try:
                                if self.is_calibrated:
                                    physical_value, _ = self.convert_to_physical_units(mean_magnitude)
                                    self.csv_writer.writerow([self.frame_count, timestamp_str, 
                                                           mean_magnitude, physical_value, mean_signal, 
                                                           self.mm_per_pixel.get()])
                                else:
                                    self.csv_writer.writerow([self.frame_count, timestamp_str, 
                                                           mean_magnitude, mean_signal])
                                self.csv_file.flush()  # Asegurar que se escriba inmediatamente
                            except Exception as e:
                                self.log_message(f"Error escribiendo a CSV de grabación: {str(e)}")
                        
                        # Enviar datos para gráficas
                        self.data_queue.put({
                            'signal': list(self.signal_buffer),
                            'frame_count': self.frame_count
                        })
                    else:
                        # Si no hay ROI, mostrar mensaje e información de ayuda
                        cv2.putText(frame, "Haz clic en 'Seleccionar ROI' para comenzar el analisis", 
                                   (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                        cv2.putText(frame, "ROI = Region de Interes para magnificacion de movimiento", 
                                   (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        cv2.putText(frame, f"Camara {self.selected_camera.get()} | FPS: {self.fps.get()}", 
                                   (10, frame.shape[0]-20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        
                    # Enviar frame para visualización (siempre, con o sin ROI)
                    try:
                        # Limpiar queue si está lleno para evitar lag
                        if self.video_queue.qsize() > 2:
                            try:
                                self.video_queue.get_nowait()
                            except queue.Empty:
                                pass
                        self.video_queue.put(frame.copy())
                    except queue.Full:
                        pass
                        
                    time.sleep(1.0 / self.fps.get())
                    
                except Exception as e:
                    self.log_message(f"Error en procesamiento: {str(e)}")
                    break
                    
        self.log_message("Loop de procesamiento terminado")
        
    def update_graphs(self):
        """Actualizar las gráficas"""
        try:
            while True:
                data = self.data_queue.get_nowait()
                
                # Actualizar gráfica de señal
                signal_data = data['signal']
                if len(signal_data) > 1:
                    self.line1.set_data(range(len(signal_data)), signal_data)
                    self.ax1.set_xlim(0, len(signal_data))
                    self.ax1.set_ylim(min(signal_data), max(signal_data))
                    
                    # Calcular y mostrar FFT
                    if len(signal_data) >= 32:  # Mínimo para FFT útil
                        signal_arr = np.array(signal_data) - np.mean(signal_data)
                        fft_vals = np.abs(np.fft.rfft(signal_arr))
                        freqs = np.fft.rfftfreq(len(signal_arr), d=1.0/self.fps.get())
                        
                        self.line2.set_data(freqs[1:], fft_vals[1:])  # Excluir DC
                        self.ax2.set_xlim(0, max(freqs))
                        self.ax2.set_ylim(0, max(fft_vals[1:]) if len(fft_vals) > 1 else 1)
                        
                        # Actualizar etiqueta del eje Y según calibración
                        if self.is_calibrated:
                            self.ax2.set_ylabel("Magnitud (mm/s)")
                            self.ax2.set_title("📈 Espectro de Velocidad (FFT)")
                        else:
                            self.ax2.set_ylabel("Magnitud (px/frame)")
                            self.ax2.set_title("📈 Espectro de Magnitudes (FFT)")
                    
                self.canvas.draw()
                
        except queue.Empty:
            pass
            
        if self.is_running and self.root.winfo_exists():
            self.root.after(100, self.update_graphs)


# Clases auxiliares del código original
def reconPyr(pyr):
    """Reconstruye la imagen a partir de su pirámide Laplaciana."""
    filt2 = pt.binomial_filter(5)
    maxLev = len(pyr)
    levs = range(0, maxLev)
    res = []
    for lev in range(maxLev-1, -1, -1):
        if lev in levs and len(res) == 0:
            res = pyr[lev]
        elif len(res) != 0:
            res_sz = res.shape
            new_sz = pyr[lev].shape
            if res_sz[0] == 1:
                hi2 = pt.upConv(image=res, filt=filt2, step=(2,1), stop=(new_sz[1], new_sz[0])).T
            elif res_sz[1] == 1:
                hi2 = pt.upConv(image=res, filt=filt2.T, step=(1,2), stop=(new_sz[1], new_sz[0])).T
            else:
                hi = pt.upConv(image=res, filt=filt2, step=(2,1), stop=(new_sz[0], res_sz[1]))
                hi2 = pt.upConv(image=hi, filt=filt2.T, step=(1,2), stop=(new_sz[0], new_sz[1]))
            if lev in levs:
                bandIm = pyr[lev]
                res = hi2 + bandIm
            else:
                res = hi2
    return res


class Magnify(object):
    """Clase para magnificar movimientos en una secuencia de imágenes."""
    def __init__(self, gray1, alpha, lambda_c, fl, fh, samplingRate):
        [low_a, low_b] = signal.butter(1, fl/samplingRate, 'low')
        [high_a, high_b] = signal.butter(1, fh/samplingRate, 'low')
        py1 = pt.pyramids.LaplacianPyramid(gray1)
        py1._build_pyr()
        pyramid_1 = py1.pyr_coeffs
        nLevels = len(pyramid_1)
        self.filtered = pyramid_1
        self.alpha = alpha
        self.fl = fl
        self.fh = fh
        self.samplingRate = samplingRate
        self.low_a = low_a
        self.low_b = low_b
        self.high_a = high_a
        self.high_b = high_b
        self.width = gray1.shape[0]
        self.height = gray1.shape[1]
        self.gray1 = img_as_float(gray1)
        self.lowpass1 = copy.deepcopy(pyramid_1)
        self.lowpass2 = copy.deepcopy(self.lowpass1)
        self.pyr_prev = copy.deepcopy(pyramid_1)
        self.filtered = [None for _ in range(nLevels)]
        self.nLevels = nLevels
        self.lambd = (self.width**2 + self.height**2) / 3.
        self.lambda_c = lambda_c
        self.delta = self.lambda_c / 8. / (1 + self.alpha)

    def Magnify(self, gray2):
        """Magnifica los movimientos en la imagen gray2."""
        gray2 = img_as_float(gray2)
        py2 = pt.pyramids.LaplacianPyramid(gray2)
        py2._build_pyr()
        pyr = py2.pyr_coeffs
        nLevels = self.nLevels
        for u in range(nLevels):
            self.lowpass1[(u,0)] = (-self.high_b[1]*self.lowpass1[(u,0)] + self.high_a[0]*pyr[(u,0)] + self.high_a[1]*self.pyr_prev[(u,0)]) / self.high_b[0]
            self.lowpass2[(u,0)] = (-self.low_b[1]*self.lowpass2[(u,0)] + self.low_a[0]*pyr[(u,0)] + self.low_a[1]*self.pyr_prev[(u,0)]) / self.low_b[0]
            self.filtered[u] = self.lowpass1[(u,0)] - self.lowpass2[(u,0)]
        self.pyr_prev = copy.deepcopy(pyr)
        exaggeration_factor = 2
        lambd = self.lambd
        delta = self.delta
        filtered = self.filtered
        for l in range(nLevels-1, -1, -1):
            currAlpha = lambd / delta / 8. - 1
            currAlpha = currAlpha * exaggeration_factor
            if (l == nLevels - 1 or l == 0):
                filtered[l] = np.zeros(np.shape(filtered[l]))
            elif (currAlpha > self.alpha):
                filtered[l] = self.alpha * filtered[l]
            else:
                filtered[l] = currAlpha * filtered[l]
            lambd = lambd / 2.
        output = reconPyr(filtered)
        output = gray2 + output
        output[output < 0] = 0
        output[output > 1] = 1
        output = img_as_ubyte(output)
        return output


if __name__ == "__main__":
    root = tk.Tk()
    app = MotionMagnificationGUI(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Aplicación cerrada por el usuario")
    finally:
        if app.camera:
            app.camera.release()
        cv2.destroyAllWindows()
