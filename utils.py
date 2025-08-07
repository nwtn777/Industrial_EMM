#!/usr/bin/env python3
"""
Utilidades para Motion Magnification GUI
Funciones auxiliares y configuración
"""

import json
import os
import logging
from datetime import datetime

def load_config(config_file='config.json'):
    """Cargar configuración desde archivo JSON"""
    default_config = {
        "default_settings": {
            "camera_id": 0,
            "fps": 10.0,
            "alpha": 200.0,
            "lambda_c": 120.0,
            "fl": 0.07,
            "fh": 3.0,
            "buffer_size": 300,
            "auto_tune_duration": 5
        },
        "gui_settings": {
            "window_width": 1200,
            "window_height": 800,
            "graph_update_interval": 100,
            "console_max_lines": 1000
        },
        "processing_settings": {
            "roi_min_size": 50,
            "gaussian_blur_kernel": [5, 5],
            "optical_flow_params": {
                "pyr_scale": 0.5,
                "levels": 3,
                "winsize": 15,
                "iterations": 3,
                "poly_n": 5,
                "poly_sigma": 1.2,
                "flags": 0
            }
        },
        "file_settings": {
            "csv_output_dir": "historiales",
            "csv_filename_format": "vibration_history_%Y%m%d_%H%M%S.csv",
            "auto_save": True
        }
    }
    
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                # Mergear con configuración por defecto
                for section in default_config:
                    if section in loaded_config:
                        default_config[section].update(loaded_config[section])
                    
        return default_config
    except Exception as e:
        print(f"Error cargando configuración: {e}")
        return default_config

def save_config(config, config_file='config.json'):
    """Guardar configuración a archivo JSON"""
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error guardando configuración: {e}")
        return False

def check_pyrtools_availability():
    """Verificar que pyrtools esté disponible como dependencia obligatoria"""
    try:
        import pyrtools
        return True, None
    except ImportError as e:
        error_msg = (
            "pyrtools es una dependencia OBLIGATORIA para Motion Magnification GUI.\n"
            "Instálalo con:\n"
            "  pip install pyrtools\n"
            "O ejecuta 'python launcher.py' para instalación automática.\n"
            "Para pruebas sin pyrtools, usa 'python demo_gui.py'"
        )
        return False, error_msg

def setup_logging(log_level=logging.INFO):
    """Configurar logging para la aplicación"""
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler('motion_magnification.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def validate_roi(roi, frame_shape, min_size=50):
    """Validar que el ROI sea válido"""
    if not roi or len(roi) != 4:
        return False
        
    x, y, w, h = roi
    frame_h, frame_w = frame_shape[:2]
    
    # Verificar límites
    if x < 0 or y < 0 or x + w > frame_w or y + h > frame_h:
        return False
        
    # Verificar tamaño mínimo
    if w < min_size or h < min_size:
        return False
        
    return True

def format_time_duration(seconds):
    """Formatear duración en segundos a formato legible"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{int(minutes)}m {int(secs)}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{int(hours)}h {int(minutes)}m"

def get_available_cameras(max_cameras=10):
    """Detectar cámaras disponibles en el sistema"""
    import cv2
    
    available_cameras = []
    
    for i in range(max_cameras):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                available_cameras.append(i)
            cap.release()
    
    return available_cameras

def calculate_memory_usage():
    """Calcular uso de memoria de la aplicación"""
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        return {
            'rss': memory_info.rss / 1024 / 1024,  # MB
            'vms': memory_info.vms / 1024 / 1024,  # MB
            'percent': process.memory_percent()
        }
    except ImportError:
        return None

def export_signal_data(signal_data, time_data, filename=None):
    """Exportar datos de señal a archivo CSV"""
    import csv
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"signal_export_{timestamp}.csv"
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Time', 'Signal'])
            
            for t, s in zip(time_data, signal_data):
                writer.writerow([t, s])
                
        return True, filename
    except Exception as e:
        return False, str(e)

class PerformanceMonitor:
    """Monitor de rendimiento para la aplicación"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.frame_times = []
        self.processing_times = []
        
    def record_frame_time(self, frame_time):
        """Registrar tiempo de procesamiento de frame"""
        self.frame_times.append(frame_time)
        
        # Mantener solo los últimos 100 frames
        if len(self.frame_times) > 100:
            self.frame_times.pop(0)
    
    def record_processing_time(self, processing_time):
        """Registrar tiempo de procesamiento general"""
        self.processing_times.append(processing_time)
        
        if len(self.processing_times) > 100:
            self.processing_times.pop(0)
    
    def get_average_fps(self):
        """Obtener FPS promedio"""
        if not self.frame_times:
            return 0
        
        avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        return 1.0 / avg_frame_time if avg_frame_time > 0 else 0
    
    def get_performance_stats(self):
        """Obtener estadísticas de rendimiento"""
        return {
            'uptime': (datetime.now() - self.start_time).total_seconds(),
            'avg_fps': self.get_average_fps(),
            'total_frames': len(self.frame_times),
            'avg_processing_time': sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        }

def check_system_requirements():
    """Verificar requisitos del sistema"""
    requirements = {
        'python_version': True,
        'memory': True,
        'opencv': True,
        'camera': True
    }
    
    import sys
    
    # Verificar versión de Python
    if sys.version_info < (3, 7):
        requirements['python_version'] = False
    
    # Verificar memoria disponible
    try:
        import psutil
        memory = psutil.virtual_memory()
        if memory.available < 1024 * 1024 * 1024:  # < 1GB
            requirements['memory'] = False
    except ImportError:
        pass  # No se puede verificar
    
    # Verificar OpenCV
    try:
        import cv2
        # Intentar acceder a una cámara
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            requirements['camera'] = False
        else:
            cap.release()
    except ImportError:
        requirements['opencv'] = False
        requirements['camera'] = False
    
    return requirements

if __name__ == "__main__":
    # Pruebas de las utilidades
    print("Probando utilidades...")
    
    # Cargar configuración
    config = load_config()
    print(f"Configuración cargada: {config['default_settings']['fps']} FPS")
    
    # Verificar cámaras disponibles
    cameras = get_available_cameras()
    print(f"Cámaras disponibles: {cameras}")
    
    # Verificar requisitos del sistema
    requirements = check_system_requirements()
    print(f"Requisitos del sistema: {requirements}")
    
    print("Utilidades funcionando correctamente!")
