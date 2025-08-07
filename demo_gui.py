#!/usr/bin/env python3
"""
Script de prueba para la interfaz GUI de Motion Magnification
Versión simplificada para testing rápido
"""

import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import time
import threading

class SimpleMotionGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Motion Magnification GUI - Demo")
        self.root.geometry("800x600")
        
        # Variables de control
        self.is_running = False
        self.selected_camera = tk.IntVar(value=0)
        self.fps = tk.DoubleVar(value=10.0)
        
        # Datos simulados
        self.time_data = []
        self.signal_data = []
        
        self.setup_ui()
        
    def setup_ui(self):
        """Configurar interfaz de usuario simplificada"""
        # Frame superior para controles
        control_frame = ttk.LabelFrame(self.root, text="Controles")
        control_frame.pack(fill='x', padx=10, pady=5)
        
        # Selección de cámara
        ttk.Label(control_frame, text="Cámara:").grid(row=0, column=0, padx=5, pady=5)
        camera_combo = ttk.Combobox(control_frame, textvariable=self.selected_camera, 
                                   values=list(range(5)), state='readonly', width=10)
        camera_combo.grid(row=0, column=1, padx=5, pady=5)
        
        # FPS
        ttk.Label(control_frame, text="FPS:").grid(row=0, column=2, padx=5, pady=5)
        fps_spinbox = ttk.Spinbox(control_frame, from_=1, to=60, textvariable=self.fps, 
                                 width=10, increment=1)
        fps_spinbox.grid(row=0, column=3, padx=5, pady=5)
        
        # Botones
        self.start_button = ttk.Button(control_frame, text="Iniciar Demo", 
                                      command=self.start_demo)
        self.start_button.grid(row=0, column=4, padx=10, pady=5)
        
        self.stop_button = ttk.Button(control_frame, text="Detener", 
                                     command=self.stop_demo, state='disabled')
        self.stop_button.grid(row=0, column=5, padx=5, pady=5)
        
        # Frame para gráficas
        graph_frame = ttk.LabelFrame(self.root, text="Señal de Vibración Simulada")
        graph_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Configurar matplotlib
        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.ax.set_title("Señal de Vibración (Simulada)")
        self.ax.set_xlabel("Tiempo (s)")
        self.ax.set_ylabel("Amplitud")
        self.ax.grid(True)
        
        self.line, = self.ax.plot([], [], 'b-', linewidth=2)
        
        # Integrar matplotlib en tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, graph_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Listo para iniciar demo")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief='sunken')
        status_bar.pack(side='bottom', fill='x')
        
    def start_demo(self):
        """Iniciar demo con datos simulados"""
        self.is_running = True
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        
        # Limpiar datos anteriores
        self.time_data.clear()
        self.signal_data.clear()
        
        self.status_var.set(f"Demo ejecutándose - Cámara {self.selected_camera.get()}")
        
        # Iniciar thread de simulación
        self.demo_thread = threading.Thread(target=self.simulate_data)
        self.demo_thread.daemon = True
        self.demo_thread.start()
        
        # Iniciar actualización de gráficas
        self.update_plot()
        
    def stop_demo(self):
        """Detener demo"""
        self.is_running = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.status_var.set("Demo detenido")
        
    def simulate_data(self):
        """Simular datos de vibración"""
        start_time = time.time()
        
        while self.is_running:
            current_time = time.time() - start_time
            
            # Simular señal de vibración con ruido
            # Componente principal + armónicos + ruido
            signal = (2.0 * np.sin(2 * np.pi * 1.5 * current_time) +  # 1.5 Hz
                     0.8 * np.sin(2 * np.pi * 3.0 * current_time) +   # 3.0 Hz
                     0.4 * np.sin(2 * np.pi * 7.5 * current_time) +   # 7.5 Hz
                     0.2 * np.random.normal())                        # Ruido
            
            self.time_data.append(current_time)
            self.signal_data.append(signal)
            
            # Mantener solo los últimos 200 puntos
            if len(self.time_data) > 200:
                self.time_data.pop(0)
                self.signal_data.pop(0)
            
            time.sleep(1.0 / self.fps.get())
            
    def update_plot(self):
        """Actualizar gráfica"""
        if self.time_data and self.signal_data:
            self.line.set_data(self.time_data, self.signal_data)
            
            # Ajustar límites
            self.ax.set_xlim(min(self.time_data), max(self.time_data))
            self.ax.set_ylim(min(self.signal_data) - 0.5, max(self.signal_data) + 0.5)
            
            self.canvas.draw()
            
        if self.is_running:
            self.root.after(50, self.update_plot)  # Actualizar cada 50ms


def main():
    """Función principal"""
    root = tk.Tk()
    
    try:
        # Verificar si tkinter está disponible
        app = SimpleMotionGUI(root)
        
        messagebox.showinfo("Demo GUI", 
                           "Este es un demo de la interfaz GUI.\n\n"
                           "Características:\n"
                           "• Selección de cámara simulada\n"
                           "• Control de FPS\n"
                           "• Gráfica en tiempo real\n"
                           "• Señal de vibración simulada\n\n"
                           "Haz clic en 'Iniciar Demo' para comenzar.")
        
        root.mainloop()
        
    except Exception as e:
        messagebox.showerror("Error", f"Error al iniciar la aplicación:\n{str(e)}")
    finally:
        print("Demo finalizado")


if __name__ == "__main__":
    main()
