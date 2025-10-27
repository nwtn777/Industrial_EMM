import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog

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
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
from functools import lru_cache

# Importar función de generación de reportes
from reporte_estadistico import generar_reportes_para_archivos

# Verificar pyrtools como dependencia obligatoria
try:
    import pyrtools as pt
except ImportError:
    import sys
    print("ERROR: pyrtools es una dependencia obligatoria para Motion Magnification GUI")
    print("Instálalo con: pip install pyrtools")
    print("O ejecuta: python launcher.py para instalación automática ")
    sys.exit(1)

from skimage import img_as_float, img_as_ubyte
import copy

class MotionMagnificationGUI:
    def optimize_alpha_lambda(self, frame, roi, alpha_range=None, lambda_range=None, metric='energy'):
        """
        Busca los mejores valores de alpha y lambda_c para maximizar la energía de movimiento en la ROI.
        Args:
            frame: Frame de entrada (BGR)
            roi: (x, y, w, h)
            alpha_range: lista o np.arange de valores alpha
            lambda_range: lista o np.arange de valores lambda_c
            metric: 'energy' (por defecto)
        Returns:
            dict con 'best_alpha', 'best_lambda', 'best_metric', 'results' (lista de dicts)
        """
        import numpy as np
        if alpha_range is None:
            alpha_range = np.linspace(50, 300, 6)  # Ejemplo: [50, 100, ..., 300]
        if lambda_range is None:
            lambda_range = np.linspace(20, 120, 6)
        x, y, w, h = roi
        roi_img = frame[y:y+h, x:x+w]
        gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
        best_metric = -np.inf
        best_alpha = None
        best_lambda = None
        results = []
        for alpha in alpha_range:
            for lambd in lambda_range:
                self.alpha.set(alpha)
                self.lambda_c.set(lambd)
                if self.magnify_engine:
                    magnified = self.magnify_engine.Magnify(gray)
                else:
                    magnified = gray
                # Métrica: energía total del movimiento (varianza de la diferencia)
                diff = cv2.absdiff(magnified, gray)
                energy = np.var(diff)
                results.append({'alpha': alpha, 'lambda': lambd, 'energy': energy})
                if energy > best_metric:
                    best_metric = energy
                    best_alpha = alpha
                    best_lambda = lambd
        # Restaurar valores óptimos
        self.alpha.set(best_alpha)
        self.lambda_c.set(best_lambda)
        self.log_message(f"Optimización alpha/lambda: alpha={best_alpha}, lambda={best_lambda}, energía={best_metric:.2f}")
        return {'best_alpha': best_alpha, 'best_lambda': best_lambda, 'best_metric': best_metric, 'results': results}
    def get_effective_fps(self):
        """Devuelve el FPS efectivo considerando el salto de frames."""
        skip = max(1, self.skip_frames.get())
        return self.fps.get() / skip
    def on_closing(self):
        """Maneja el evento de cierre de la ventana principal."""
        import sys
        try:
            self.is_running = False
            if hasattr(self, 'camera') and self.camera:
                self.camera.release()
            if hasattr(self, 'csv_file') and self.csv_file:
                self.csv_file.close()
            cv2.destroyAllWindows()
        except Exception as e:
            self.log_message(f"Error al cerrar la aplicación: {str(e)}")
        finally:
            self.root.destroy()
            sys.exit(0)
    def __init__(self, root):
        self.root = root
        self.root.title("Motion Magnification - Sistema de Monitoreo de Vibraciones")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 700)
        
        # Agregar manejo de cierre de ventana
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Variables de control
        self.camera = None
        self.is_running = False
        self.selected_camera = tk.IntVar(value=0)
        self.fps = tk.DoubleVar(value=30.0)
        self.alpha = tk.DoubleVar(value=200.0)
        self.lambda_c = tk.DoubleVar(value=80.0)
        self.fl = tk.DoubleVar(value=0.5)
        self.fh = tk.DoubleVar(value=9)

        # Añadimos estas variables para mantener compatibilidad, pero no se usan
        self.use_frame_skip = tk.BooleanVar(value=False)  # Siempre desactivado
        self.skip_frames = tk.IntVar(value=1)  # Siempre 1 (no saltar frames)
        self.frame_skip_counter = 0
        
        # Variables para calibración física
        self.mm_per_pixel = tk.DoubleVar(value=0.1)  # mm por píxel (calibrar)
        self.is_calibrated = False
        self.calibration_distance_mm = tk.DoubleVar(value=10.0)  # distancia conocida en mm
        
        # Variables para filtro FFT de frecuencias bajas
        self.fft_highpass_enabled = tk.BooleanVar(value=False)  # Activar/desactivar filtro
        self.fft_cutoff_freq = tk.DoubleVar(value=0.5)  # Frecuencia de corte en Hz
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
        
        # --- Variables para optimización y procesamiento paralelo ---
        # ThreadPoolExecutor para procesamiento paralelo
        self.max_workers = min(4, multiprocessing.cpu_count())
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # Cache para pirámides y cálculos repetitivos
        self.pyramid_cache = {}
        self.flow_cache = {}
        
        # Buffer de frames para procesamiento asíncrono
        self.frame_processing_queue = queue.Queue(maxsize=10)
        self.processed_frame_queue = queue.Queue(maxsize=5)
        
        # Control de rendimiento
        self.processing_times = deque(maxlen=10)  # Para monitoreo de rendimiento
        self.adaptive_quality = False  # Desactivado para evitar salto automático de frames
        
        # Flags de optimización
        self.use_parallel_processing = tk.BooleanVar(value=True)
        
        # Método de vibración: 'brillo' o 'flujo'
        self.vibration_method = tk.StringVar(value='brillo')
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

        # --- Pestaña 3: Reporte Estadístico ---
        report_tab = ttk.Frame(notebook)
        notebook.add(report_tab, text="Reporte Estadístico")
        self.setup_report_tab(report_tab)

    def setup_report_tab(self, parent):
        """Configura la pestaña de generación de reportes PDF estadísticos."""
        label = ttk.Label(parent, text="Generar reporte PDF estadístico de archivos CSV de señal.", font=("Arial", 12))
        label.pack(pady=20)

        btn = ttk.Button(parent, text="Seleccionar archivos CSV y generar reporte", command=self.handle_generate_report)
        btn.pack(pady=10)

        self.report_status = ttk.Label(parent, text="", foreground="blue")
        self.report_status.pack(pady=10)

    def handle_generate_report(self):
        file_paths = filedialog.askopenfilenames(
            title='Selecciona uno o más archivos CSV',
            filetypes=[('Archivos CSV', '*.csv')]
        )
        if not file_paths:
            return
        self.report_status.config(text="Generando reportes, por favor espera...")
        self.root.update_idletasks()
        try:
            pdfs = generar_reportes_para_archivos(file_paths)
            if pdfs:
                msg = "Reportes generados:\n" + "\n".join(pdfs)
                self.report_status.config(text=msg, foreground="green")
                messagebox.showinfo("Listo", msg)
            else:
                self.report_status.config(text="No se generaron reportes.", foreground="orange")
        except Exception as e:
            self.report_status.config(text=f"Error: {e}", foreground="red")
            messagebox.showerror("Error", f"Error generando reportes: {e}")
        
    def setup_control_panel(self, parent):
        """Configurar el panel de control"""
        # Frame superior para configuración
        config_frame = ttk.LabelFrame(parent, text="Configuración de Parámetros")
        config_frame.pack(fill='x', padx=5, pady=5)

        # Botón para optimización automática de alpha/lambda
        def run_auto_opt():
            # Usar el frame actual y la ROI actual
            frame = self.current_frame
            roi = getattr(self, 'roi', None)
            if frame is None or roi is None:
                messagebox.showwarning("Advertencia", "No hay frame o ROI disponible para optimizar.")
                return
            self.log_message("Iniciando optimización automática de alpha/lambda...")
            result = self.optimize_alpha_lambda(frame, roi)
            messagebox.showinfo("Optimización completa", f"Alpha óptimo: {result['best_alpha']}\nLambda óptimo: {result['best_lambda']}\nEnergía: {result['best_metric']:.2f}")

        opt_btn = ttk.Button(config_frame, text="Optimizar Alpha/Lambda automáticamente", command=run_auto_opt)
        opt_btn.grid(row=1, column=4, padx=10, pady=2, sticky='w')

        # Selección de método de vibración
        ttk.Label(config_frame, text="Método de vibración:").grid(row=11, column=0, sticky='w', padx=5, pady=2)
        metodo_frame = ttk.Frame(config_frame)
        metodo_frame.grid(row=11, column=1, columnspan=3, sticky='w', padx=5, pady=2)
        ttk.Radiobutton(metodo_frame, text="Brillo (intensidad)", variable=self.vibration_method, value='brillo').pack(side='left', padx=2)
        ttk.Radiobutton(metodo_frame, text="Flujo óptico", variable=self.vibration_method, value='flujo').pack(side='left', padx=2)

        help_text = (
            "Alpha (amplificación): 10-50 = baja, 100-200 = recomendado, >300 = solo para señales muy limpias.\n"
            "Lambda_c (escala espacial): 10-50 = detalles finos, 100-200 = piezas grandes, >300 = objetos muy grandes.\n"
            "Recomendado: Alpha 150-200 y Lambda_c 100-150 para vibraciones industriales.\n"
            "Ajusta alpha para más/menos sensibilidad y lambda_c según el tamaño de la estructura que te interesa."
        )
        ttk.Label(config_frame, text=help_text, foreground="blue", font=("Arial", 8), justify="left", wraplength=600).grid(
            row=12, column=0, columnspan=4, sticky='w', padx=5, pady=(8, 2))
        
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
        
        # Filtro FFT de frecuencias bajas
        ttk.Label(config_frame, text="🔽 Filtro FFT:", font=('Arial', 8, 'bold')).grid(
            row=3, column=0, columnspan=2, sticky='w', padx=5, pady=2)
        
        fft_filter_check = ttk.Checkbutton(config_frame, text="Filtrar freq. bajas", 
                                          variable=self.fft_highpass_enabled)
        fft_filter_check.grid(row=3, column=2, columnspan=2, sticky='w', padx=5, pady=2)
        
        ttk.Label(config_frame, text="Corte (Hz):").grid(row=4, column=0, sticky='w', padx=5, pady=2)
        cutoff_spinbox = ttk.Spinbox(config_frame, from_=0.1, to=10, textvariable=self.fft_cutoff_freq, 
                                   width=8, increment=0.1, format="%.1f")
        cutoff_spinbox.grid(row=4, column=1, padx=5, pady=2)
        
        # Calibración física
        calib_separator = ttk.Separator(config_frame, orient='horizontal')
        calib_separator.grid(row=5, column=0, columnspan=4, sticky='ew', pady=5)
        
        ttk.Label(config_frame, text="📏 Calibración Física", font=('Arial', 9, 'bold')).grid(
            row=6, column=0, columnspan=4, pady=2)
        
        ttk.Label(config_frame, text="Dist. real (mm):").grid(row=7, column=0, sticky='w', padx=5, pady=2)
        calib_dist_spinbox = ttk.Spinbox(config_frame, from_=1, to=1000, textvariable=self.calibration_distance_mm, 
                                        width=8, increment=1, format="%.1f")
        calib_dist_spinbox.grid(row=7, column=1, padx=5, pady=2)
        
        ttk.Label(config_frame, text="Píxeles:").grid(row=7, column=2, sticky='w', padx=5, pady=2)
        calib_pixels_spinbox = ttk.Spinbox(config_frame, from_=1, to=5000, textvariable=self.calibration_pixels, 
                                          width=8, increment=1)
        calib_pixels_spinbox.grid(row=7, column=3, padx=5, pady=2)
        
        # Sección de optimización de rendimiento
        optim_separator = ttk.Separator(config_frame, orient='horizontal')
        optim_separator.grid(row=8, column=0, columnspan=4, sticky='ew', pady=5)
        
        ttk.Label(config_frame, text=" Optimización de Rendimiento", font=('Arial', 9, 'bold')).grid(
            row=9, column=0, columnspan=4, pady=2)
        
        # Procesamiento paralelo
        parallel_check = ttk.Checkbutton(config_frame, text="Procesamiento paralelo", 
                                        variable=self.use_parallel_processing)
        parallel_check.grid(row=10, column=0, columnspan=2, sticky='w', padx=5, pady=2)
        
        # Información de rendimiento
        ttk.Label(config_frame, text=f"CPUs detectadas: {multiprocessing.cpu_count()}", 
                 font=('Arial', 8, 'italic')).grid(row=10, column=2, columnspan=2, sticky='w', padx=5, pady=2)
        
        
        # Botones de control
        button_frame = ttk.LabelFrame(parent, text="Controles de Monitoreo")
        button_frame.pack(fill='x', padx=5, pady=5)
        
        # Primera fila de botones
        button_row1 = ttk.Frame(button_frame)
        button_row1.pack(pady=5)
        
        self.start_button = ttk.Button(button_row1, text="▶ Iniciar", command=self.start_monitoring)
        self.start_button.pack(side='left', padx=5)
        
        self.start_no_calib_button = ttk.Button(button_row1, text="▶ Iniciar Sin Calibración de Ruido", 
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
        
        self.auto_tune_button = ttk.Button(button_row2, text="Auto-tune", 
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

        # Botones de grabación CSV
        button_frame = ttk.Frame(graph_label_frame)
        button_frame.pack(fill='x', padx=5, pady=(5, 0))
        self.graph_record_button = ttk.Button(button_frame, text="🔴 Iniciar Grabación CSV", command=self.start_recording)
        self.graph_record_button.pack(side='left', padx=5)
        self.graph_stop_record_button = ttk.Button(button_frame, text="⏺ Detener Grabación", command=self.stop_recording, state='disabled')
        self.graph_stop_record_button.pack(side='left', padx=5)

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

        # Sincronizar estado de botones con los de la pestaña de controles
        self.update_graph_record_buttons()

    def update_graph_record_buttons(self):
        """Sincroniza el estado de los botones de grabación en la pestaña de gráficas."""
        if hasattr(self, 'is_recording') and self.is_recording:
            self.graph_record_button.config(state='disabled')
            self.graph_stop_record_button.config(state='normal')
        else:
            self.graph_record_button.config(state='normal')
            self.graph_stop_record_button.config(state='disabled')
        
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
            # Reinicializar el ThreadPoolExecutor si es necesario
            if hasattr(self, 'executor') and self.executor._shutdown:
                self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
            elif not hasattr(self, 'executor'):
                self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
            
            # Inicializar cámara
            camera_id = self.selected_camera.get()
            self.camera = cv2.VideoCapture(camera_id)
            
            if not self.camera.isOpened():
                messagebox.showerror("Error", f"No se pudo abrir la cámara {camera_id}")
                return
                
            # Ya no se usa calibración de ruido
            if not use_calibration:
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
            # self.calibrate_noise_button ya no existe
            
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
            self.camera = None
            
        cv2.destroyAllWindows()
        
        # Limpiar estado del sistema para permitir reinicio limpio
        self.roi = None
        self.magnify_engine = None
        self.frame_count = 0
        self.signal_buffer.clear()
        
        # Limpiar caches
        self.pyramid_cache.clear()
        self.flow_cache.clear()
        
        # Cerrar ThreadPoolExecutor para evitar errores en el reinicio
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)
        
        # Limpiar buffers de video
        while not self.video_queue.empty():
            try:
                self.video_queue.get_nowait()
            except:
                break
                
        while not self.data_queue.empty():
            try:
                self.data_queue.get_nowait()
            except:
                break
        
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
        
        # Limpiar video display
        self.video_label.config(image="", text="📹 El video aparecerá aquí cuando inicies el monitoreo")
        
        self.log_message("Monitoreo detenido - Sistema listo para nueva configuración")
        
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
            # Actualizar campo de píxeles automáticamente
            self.calibration_pixels.set(int(round(pixel_distance)))
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
        Aplica un único filtro Gaussiano ligero para detección óptima de vibración.
        """
        noise_level = self.noise_reduction_level.get()
        kernel_size = max(3, int(noise_level * 2) + 1)
        if kernel_size % 2 == 0:
            kernel_size += 1
        filtered_frame = cv2.GaussianBlur(frame, (kernel_size, kernel_size), noise_level)
        return filtered_frame
        
    def apply_roi_noise_filtering(self, roi_gray):
        """
        Versión simplificada para ROI que evita el sobre-procesamiento.
        Aplica sólo un filtro gaussiano controlado.
        """
        filtered_roi = roi_gray.copy()
        noise_level = self.noise_reduction_level.get()
        
        # Aplicar un único filtro gaussiano con parámetros adaptados a la intensidad de ruido
        kernel_size = max(3, int(noise_level * 1.5) + 1)
        if kernel_size % 2 == 0:
            kernel_size += 1
            
        filtered_roi = cv2.GaussianBlur(filtered_roi, (kernel_size, kernel_size), noise_level/2)
        
        return filtered_roi
        
    # --- FUNCIONES DE OPTIMIZACIÓN Y PROCESAMIENTO PARALELO ---
    
    @lru_cache(maxsize=32)
    def create_cached_pyramid(self, frame_hash, alpha, lambda_c, fl, fh, sampling_rate):
        """Crear pirámide con cache para evitar recálculos"""
        # Esta función se llamará desde el procesamiento principal
        pass  # Se implementa en el contexto donde se tiene acceso al frame
    
    def process_frame_parallel(self, frame, roi, prev_gray=None):
        """Procesar frame usando múltiples threads para diferentes tareas"""
        if not self.use_parallel_processing.get():
            # Procesamiento secuencial tradicional
            return self.process_frame_sequential(frame, roi, prev_gray)
            
        # Preparar tareas para procesamiento paralelo
        futures = []
        
        # Task 1: Magnificación de movimiento
        future_magnify = self.executor.submit(self.magnify_roi_task, frame, roi)
        futures.append(('magnify', future_magnify))
        
        # Task 2: Cálculo de flujo óptico (si hay frame previo)
        if prev_gray is not None:
            future_flow = self.executor.submit(self.optical_flow_task, prev_gray, frame, roi)
            futures.append(('flow', future_flow))
        
        # Task 3: Filtros de ruido (en paralelo si están activados)
        if (self.background_subtraction.get() or 
            self.morphological_filtering.get() or 
            self.temporal_smoothing.get()):
            future_filters = self.executor.submit(self.apply_filters_task, frame, roi)
            futures.append(('filters', future_filters))
        
        # Recopilar resultados
        results = {}
        for task_name, future in futures:
            try:
                results[task_name] = future.result(timeout=0.1)  # Timeout para evitar bloqueos
            except Exception as e:
                self.log_message(f"Error en tarea paralela {task_name}: {str(e)}")
                results[task_name] = None
        
        return results
    
    def magnify_roi_task(self, frame, roi):
        """Tarea de magnificación que se ejecuta en thread separado"""
        try:
            x, y, w, h = roi
            roi_img = frame[y:y+h, x:x+w]
            
            # Convertir a escala de grises
            if len(roi_img.shape) == 3:
                gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
            else:
                gray = roi_img.copy()
            
            # Aplicar magnificación usando el motor existente
            if self.magnify_engine:
                magnified = self.magnify_engine.Magnify(gray)
                return magnified
            else:
                return gray
                
        except Exception as e:
            self.log_message(f"Error en magnificación paralela: {str(e)}")
            return None
    
    def optical_flow_task(self, prev_gray, current_frame, roi):
        """Tarea de flujo óptico en thread separado"""
        try:
            x, y, w, h = roi
            current_roi = current_frame[y:y+h, x:x+w]
            if len(current_roi.shape) == 3:
                current_gray = cv2.cvtColor(current_roi, cv2.COLOR_BGR2GRAY)
            else:
                current_gray = current_roi.copy()

            # prev_gray debe ser del mismo tamaño que current_gray
            if prev_gray is not None and prev_gray.shape == current_gray.shape:
                flow = cv2.calcOpticalFlowFarneback(prev_gray, current_gray, None, 
                                                   0.5, 3, 15, 3, 5, 1.2, 0)
                mag = np.linalg.norm(flow, axis=2)
                mean_magnitude = np.mean(mag)
                return mean_magnitude, current_gray
            else:
                return 0, current_gray
        except Exception as e:
            self.log_message(f"Error en flujo óptico paralelo: {str(e)}")
            return 0, None
    
    def apply_filters_task(self, frame, roi):
        """Aplicar filtros de ruido en thread separado"""
        try:
            x, y, w, h = roi
            roi_frame = frame[y:y+h, x:x+w]
            
            # Aplicar filtros según configuración
            filtered_frame = self.apply_noise_filtering(roi_frame, roi)
            return filtered_frame
            
        except Exception as e:
            self.log_message(f"Error en filtros paralelos: {str(e)}")
            return roi_frame
    
    def process_frame_sequential(self, frame, roi, prev_gray=None):
        """Procesamiento secuencial tradicional (fallback)"""
        try:
            x, y, w, h = roi
            roi_img = frame[y:y+h, x:x+w]
            
            # Magnificación
            gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
            out = self.magnify_engine.Magnify(gray) if self.magnify_engine else gray
            
            # Flujo óptico
            mean_magnitude = 0
            if prev_gray is not None:
                flow = cv2.calcOpticalFlowFarneback(prev_gray, out, None, 
                                                  0.5, 3, 15, 3, 5, 1.2, 0)
                mean_magnitude = np.mean(cv2.norm(flow, cv2.NORM_L2))
            
            return {
                'magnify': out,
                'flow': (mean_magnitude, out),
                'filters': None
            }
            
        except Exception as e:
            self.log_message(f"Error en procesamiento secuencial: {str(e)}")
            return None
    
    def should_skip_frame(self):
        """Eliminada la funcionalidad de saltar frames - siempre procesar todos los frames"""
        return False
    
    def monitor_performance(self, processing_time):
        """Monitorear rendimiento sin ajustes automáticos de frame skipping"""
        self.processing_times.append(processing_time)
        
        if len(self.processing_times) >= 5:  # Evaluar cada 5 frames
            avg_time = sum(self.processing_times) / len(self.processing_times)
            target_fps = self.fps.get()
            target_time = 1.0 / target_fps;
            
            # Solo registrar el rendimiento sin activar optimizaciones automáticas
            if avg_time > target_time * 1.5:
                self.log_message(f" Rendimiento: {avg_time:.3f}s/frame (objetivo: {target_time:.3f}s)")
    
    def update_noise_filter_status(self):
        """Actualizar el estado visual de los filtros de ruido"""
        active_filters = []
        
    # Ya no se usa calibración de ruido
        
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
            os.makedirs("historiales", exist_ok=True)
            self.csv_file = open(self.recording_filename, mode='w', newline='')
            self.csv_writer = csv.writer(self.csv_file)
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
            # Actualizar botones de la pestaña de gráficas
            if hasattr(self, 'graph_record_button'):
                self.update_graph_record_buttons()
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
            # Actualizar botones de la pestaña de gráficas
            if hasattr(self, 'graph_record_button'):
                self.update_graph_record_buttons()
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
        # FPS efectivo
        fps_eff = self.get_effective_fps()
        # Convertir a mm/s
        time_per_frame = 1.0 / fps_eff  # segundos por frame efectivo
        mm_per_second = mm_per_frame / time_per_frame
        return mm_per_second, "mm/s"
        
    def auto_tune_fl_fh(self, signal_buffer, fps):
        """Ajustar automáticamente fl y fh usando picos del espectro"""
        from scipy.signal import find_peaks
        signal_arr = np.array(signal_buffer) - np.mean(signal_buffer)
        fft_vals = np.abs(np.fft.rfft(signal_arr))
        freqs = np.fft.rfftfreq(len(signal_arr), d=1.0/self.get_effective_fps())

        # Aplicar filtro paso alto si está habilitado para el análisis
        if self.fft_highpass_enabled.get():
            cutoff = self.fft_cutoff_freq.get()
            cutoff_idx = np.searchsorted(freqs, cutoff)
            if cutoff_idx > 0:
                fft_vals[:cutoff_idx] = 0  # Suprimir frecuencias bajas para análisis

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
        """Loop principal de procesamiento optimizado"""
        self.log_message("Iniciando loop de procesamiento optimizado...")
        self.log_message(f" Usando {self.max_workers} threads para procesamiento paralelo")
        
        prev_gray = None
        
        while self.is_running:
            try:
                frame_start_time = time.time();
                

                ret, frame = self.camera.read()
                if not ret:
                    break

                # Actualizar el frame actual para optimización y GUI
                self.current_frame = frame.copy()

                self.frame_count += 1

                # Verificar si se debe saltar este frame para mejorar rendimiento
                if self.should_skip_frame():
                    continue
                
                # Procesar solo si hay ROI y motor de magnificación
                if self.roi and self.magnify_engine:
                    # FPS efectivo para cálculos
                    fps_eff = self.get_effective_fps()
                    # Usar procesamiento paralelo u optimizado
                    processing_results = self.process_frame_parallel(frame, self.roi, prev_gray)
                    
                    if processing_results:
                        # Extraer resultados
                        magnified_result = processing_results.get('magnify')
                        flow_result = processing_results.get('flow')
                        
                        if magnified_result is not None:
                            out = magnified_result
                            prev_gray = out.copy()
                            
                            # Actualizar frame original con resultado magnificado
                            x, y, w, h = self.roi
                            frame[y:y+h, x:x+w] = cv2.cvtColor(out, cv2.COLOR_GRAY2BGR)
                            
                            # Obtener magnitud del flujo óptico
                            mean_magnitude = 0
                            if flow_result and len(flow_result) == 2:
                                mean_magnitude, _ = flow_result
                            
                            # Dibujar información del ROI
                            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 3)
                            
                            # Convertir a unidades físicas si está calibrado
                            physical_value, physical_units = self.convert_to_physical_units(mean_magnitude)
                            
                            # Mostrar información optimizada
                            if self.is_calibrated:
                                info_text = f"ROI: {w}x{h} | Vel: {physical_value:.2f} {physical_units}"
                            else:
                                info_text = f"ROI: {w}x{h} | Mag: {mean_magnitude:.2f} px/frame"
                            
                            cv2.putText(frame, info_text, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 
                                       0.6, (0, 255, 0), 2)
                            
                            # Información de rendimiento
                            processing_time = time.time() - frame_start_time;
                            fps_actual = 1.0 / processing_time if processing_time > 0 else 0
                            
                            # Mostrar parámetros y rendimiento
                            params_text = f"alpha:{self.alpha.get():.0f} | fl:{self.fl.get():.3f} | fh:{self.fh.get():.2f} | FPS:{fps_actual:.1f}"
                            cv2.putText(frame, params_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                                       0.5, (255, 255, 255), 1)
                            
                            # Mostrar estado de optimizaciones
                            if self.use_parallel_processing.get() or self.use_frame_skip.get():
                                optim_text = f""
                                if self.use_parallel_processing.get():
                                    optim_text += f" Parallel({self.max_workers})"
                                if self.use_frame_skip.get():
                                    optim_text += f" Skip(1/{self.skip_frames.get()})"
                                cv2.putText(frame, optim_text, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 
                                           0.4, (0, 255, 255), 1)
                            

                            # Datos para gráficas según método seleccionado
                            if self.vibration_method.get() == 'flujo':
                                # Usar la magnitud promedio del flujo óptico
                                if flow_result and len(flow_result) == 2:
                                    mean_signal = flow_result[0]
                                else:
                                    mean_signal = 0
                            else:
                                # Usar el brillo promedio del ROI magnificado
                                if out is not None:
                                    mean_signal = np.mean(out)
                                else:
                                    mean_signal = 0
                            self.signal_buffer.append(mean_signal)
                            
                            # Guardar en CSV de grabación solo si está activa
                            if self.is_recording and self.csv_writer:
                                try:
                                    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    if self.is_calibrated:
                                        self.csv_writer.writerow([self.frame_count, timestamp_str, 
                                                               mean_magnitude, physical_value, mean_signal, 
                                                               self.mm_per_pixel.get()])
                                    else:
                                        self.csv_writer.writerow([self.frame_count, timestamp_str, 
                                                               mean_magnitude, mean_signal])
                                    self.csv_file.flush()
                                except Exception as e:
                                    self.log_message(f"Error escribiendo a CSV de grabación: {str(e)}")
                            
                            # Enviar datos para gráficas
                            try:
                                self.data_queue.put({
                                    'signal': list(self.signal_buffer),
                                    'frame_count': self.frame_count
                                }, block=False)
                            except queue.Full:
                                pass  # Skip si la queue está llena
                            
                            # Monitorear rendimiento y optimizar automáticamente
                            self.monitor_performance(processing_time)
                            
                else:
                    # Si no hay ROI, mostrar mensaje optimizado
                    cv2.putText(frame, "Selecciona ROI para comenzar analisis", 
                               (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    cv2.putText(frame, f"Cam {self.selected_camera.get()} | FPS: {self.fps.get()}", 
                               (10, frame.shape[0]-20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    
                # Enviar frame para visualización con control de queue
                try:
                    # Limpiar queue si está lleno para evitar lag
                    while self.video_queue.qsize() > 2:
                        try:
                            self.video_queue.get_nowait()
                        except queue.Empty:
                            break
                    self.video_queue.put(frame.copy(), block=False)
                except queue.Full:
                    pass  # Skip frame si no hay espacio
                
                # Control de FPS adaptativo
                target_frame_time = 1.0 / self.fps.get()
                elapsed_time = time.time() - frame_start_time
                if elapsed_time < target_frame_time:
                    time.sleep(target_frame_time - elapsed_time)
                    
            except Exception as e:
                self.log_message(f"Error en procesamiento: {str(e)}")
                time.sleep(0.1)  # Pausa breve antes de reintentar
                
        # Limpiar recursos al terminar
        self.executor.shutdown(wait=False)
        self.log_message("Loop de procesamiento terminado")
        
    def update_graphs(self):
        """Actualizar las gráficas"""
        try:
            while True:
                data = self.data_queue.get_nowait()
                signal_data = data['signal']
                if len(signal_data) > 1:
                    x_vals = range(len(signal_data))
                    self.line1.set_data(x_vals, signal_data)
                    self.ax1.set_xlim(0, len(signal_data))
                    # Mejorar escala y márgenes
                    y_min, y_max = min(signal_data), max(signal_data)
                    y_pad = (y_max - y_min) * 0.1 if y_max > y_min else 1
                    self.ax1.set_ylim(y_min - y_pad, y_max + y_pad)

                    # Etiquetas y unidades dinámicas
                    if self.vibration_method.get() == 'flujo':
                        y_label = "Magnitud media flujo óptico"
                    else:
                        y_label = "Brillo medio ROI"
                    if self.is_calibrated:
                        y_label += " (mm/s)"
                    else:
                        y_label += " (px/frame)"
                    self.ax1.set_ylabel(y_label)

                    # Título dinámico
                    method = self.vibration_method.get()
                    if method == 'flujo':
                        title = "Señal de Vibración (Flujo óptico)"
                    else:
                        title = "Señal de Vibración (Brillo)"
                    self.ax1.set_title(title, fontsize=12, fontweight='bold')

                    # Estadísticas señal
                    rms = np.sqrt(np.mean(np.square(signal_data)))
                    mean = np.mean(signal_data)
                    min_val = np.min(signal_data)
                    max_val = np.max(signal_data)
                    stats_text = f"RMS: {rms:.2f}  Media: {mean:.2f}  Min: {min_val:.2f}  Max: {max_val:.2f}"
                    # Borrar textos previos
                    if hasattr(self, '_signal_stats_text') and self._signal_stats_text:
                        self._signal_stats_text.remove()
                    self._signal_stats_text = self.ax1.text(0.01, 0.98, stats_text, transform=self.ax1.transAxes,
                        fontsize=9, color='black', verticalalignment='top', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

                    # Líneas de referencia
                    for line in getattr(self, '_signal_ref_lines', []):
                        line.remove()
                    self._signal_ref_lines = [
                        self.ax1.axhline(mean, color='g', linestyle='--', linewidth=1, alpha=0.5, label='Media'),
                        self.ax1.axhline(rms, color='m', linestyle=':', linewidth=1, alpha=0.5, label='RMS'),
                    ]

                    self.ax1.grid(True, which='both', linestyle=':', alpha=0.4)
                    self.ax1.legend(loc='upper right', fontsize=9, frameon=True)

                    # FFT con filtro pasa-alta real si está habilitado
                    if len(signal_data) >= 32:
                        signal_arr = np.array(signal_data) - np.mean(signal_data)
                        freqs = np.fft.rfftfreq(len(signal_arr), d=1.0/self.get_effective_fps())
                        fft_vals = None
                        # Filtro pasa-alta real
                        if self.fft_highpass_enabled.get():
                            from scipy.signal import butter, filtfilt
                            cutoff = self.fft_cutoff_freq.get()
                            fs = self.get_effective_fps()
                            # Normalizar frecuencia de corte
                            wn = cutoff / (0.5 * fs)
                            if wn < 1.0:
                                b, a = butter(2, wn, btype='high')
                                filtered_signal = filtfilt(b, a, signal_arr)
                                fft_vals = np.abs(np.fft.rfft(filtered_signal))
                            else:
                                fft_vals = np.abs(np.fft.rfft(signal_arr))
                        else:
                            fft_vals = np.abs(np.fft.rfft(signal_arr))

                        # Graficar FFT
                        self.line2.set_data(freqs[1:], fft_vals[1:])
                        fft_xmax = 15
                        if self.fft_highpass_enabled.get():
                            cutoff = self.fft_cutoff_freq.get()
                            self.ax2.set_xlim(cutoff, fft_xmax)
                            if len(freqs) > 1:
                                self.ax2.set_ylim(0, max(fft_vals[1:]) * 1.1)
                            else:
                                self.ax2.set_ylim(0, 1)
                        else:
                            self.ax2.set_xlim(0, fft_xmax)
                            self.ax2.set_ylim(0, max(fft_vals[1:]) * 1.1 if len(fft_vals) > 1 else 1)

                        # Etiquetas y título FFT
                        if self.is_calibrated:
                            self.ax2.set_ylabel("Magnitud (mm/s)")
                            self.ax2.set_title("Espectro de Velocidad (FFT)")
                        else:
                            self.ax2.set_ylabel("Magnitud (px/frame)")
                            self.ax2.set_title("Espectro de Frecuencias (FFT)")

                        # Estadísticas FFT
                        fft_peak_idx = np.argmax(fft_vals[1:]) + 1 if len(fft_vals) > 1 else 0
                        fft_peak_freq = freqs[fft_peak_idx] if fft_peak_idx > 0 else 0
                        fft_peak_val = fft_vals[fft_peak_idx] if fft_peak_idx > 0 else 0
                        fft_stats = f"Pico: {fft_peak_freq:.2f} Hz ({fft_peak_val:.2f})"
                        if hasattr(self, '_fft_stats_text') and self._fft_stats_text:
                            self._fft_stats_text.remove()
                        self._fft_stats_text = self.ax2.text(0.01, 0.98, fft_stats, transform=self.ax2.transAxes,
                            fontsize=9, color='black', verticalalignment='top', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

                        # Línea de referencia en pico
                        for line in getattr(self, '_fft_ref_lines', []):
                            line.remove()
                        self._fft_ref_lines = []
                        if fft_peak_idx > 0:
                            self._fft_ref_lines.append(
                                self.ax2.axvline(fft_peak_freq, color='r', linestyle='--', linewidth=1, alpha=0.5, label='Pico')
                            )

                        self.ax2.grid(True, which='both', linestyle=':', alpha=0.4)
                        self.ax2.legend(loc='upper right', fontsize=9, frameon=True)

                    self.canvas.draw()
        except queue.Empty:
            pass
        if self.root.winfo_exists():
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
        exaggeration_factor = 3 # Factor de exageración para mejorar visibilidad
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
