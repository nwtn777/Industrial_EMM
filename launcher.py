#!/usr/bin/env python3
"""
Launcher para Motion Magnification GUI
Detecta dependencias y ofrece opciones de ejecución
"""

import sys
import subprocess
import importlib.util
import tkinter as tk
from tkinter import messagebox, ttk

def check_dependency(module_name, package_name=None):
    """Verificar si un módulo está instalado"""
    if package_name is None:
        package_name = module_name
    
    spec = importlib.util.find_spec(module_name)
    return spec is not None, package_name

def install_package(package_name):
    """Instalar un paquete usando pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        return True
    except subprocess.CalledProcessError:
        return False

class DependencyChecker:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Motion Magnification - Dependency Checker")
        self.root.geometry("600x400")
        
        # Lista de dependencias requeridas
        self.dependencies = [
            ("cv2", "opencv-contrib-python"),
            ("numpy", "numpy"),
            ("matplotlib", "matplotlib"),
            ("scipy", "scipy"),
            ("skimage", "scikit-image"),
            ("PIL", "pillow"),
            ("pyrtools", "pyrtools"),
            ("pandas", "pandas"),
            ("fpdf", "fpdf")
        ]
        
        # Dependencia opcional (actualmente ninguna)
        self.optional_deps = [
            # No hay dependencias opcionales actualmente
        ]
        
        self.setup_ui()
        self.check_all_dependencies()
        
    def setup_ui(self):
        """Configurar interfaz de usuario"""
        # Título
        title_label = tk.Label(self.root, text="Motion Magnification GUI", 
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        subtitle_label = tk.Label(self.root, text="Verificador de Dependencias", 
                                 font=("Arial", 10))
        subtitle_label.pack()
        
        # Frame para lista de dependencias
        deps_frame = ttk.LabelFrame(self.root, text="Estado de Dependencias")
        deps_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Crear Treeview para mostrar dependencias
        self.tree = ttk.Treeview(deps_frame, columns=('Status', 'Package'), show='tree headings')
        self.tree.heading('#0', text='Módulo')
        self.tree.heading('Status', text='Estado')
        self.tree.heading('Package', text='Paquete')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(deps_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Frame para botones
        button_frame = tk.Frame(self.root)
        button_frame.pack(fill='x', padx=20, pady=10)
        
        self.install_button = tk.Button(button_frame, text="Instalar Faltantes", 
                                       command=self.install_missing, bg='orange')
        self.install_button.pack(side='left', padx=5)
        
        
        self.full_button = tk.Button(button_frame, text="Ejecutar GUI Completa", 
                                    command=self.run_full_gui, bg='lightgreen')
        self.full_button.pack(side='left', padx=5)
        
        self.quit_button = tk.Button(button_frame, text="Salir", 
                                    command=self.root.quit, bg='lightcoral')
        self.quit_button.pack(side='right', padx=5)
        
        # Área de texto para información
        info_frame = ttk.LabelFrame(self.root, text="Información")
        info_frame.pack(fill='x', padx=20, pady=(0, 10))
        
        self.info_text = tk.Text(info_frame, height=6, wrap='word')
        self.info_text.pack(fill='both', expand=True, padx=5, pady=5)
        
    def log_info(self, message):
        """Agregar mensaje al área de información"""
        self.info_text.insert('end', message + '\n')
        self.info_text.see('end')
        self.root.update()
        
    def check_all_dependencies(self):
        """Verificar todas las dependencias"""
        self.log_info("Verificando dependencias...")
        
        self.missing_deps = []
        self.optional_missing = []
        
        # Verificar dependencias principales
        for module, package in self.dependencies:
            is_installed, pkg_name = check_dependency(module, package)
            
            if is_installed:
                item = self.tree.insert('', 'end', text=module, 
                                       values=('✅ Instalado', pkg_name),
                                       tags=('installed',))
            else:
                item = self.tree.insert('', 'end', text=module, 
                                       values=('❌ Faltante', pkg_name),
                                       tags=('missing',))
                self.missing_deps.append(package)
        
        # Verificar dependencias opcionales
        for module, package in self.optional_deps:
            is_installed, pkg_name = check_dependency(module, package)
            
            if is_installed:
                item = self.tree.insert('', 'end', text=f"{module} (opcional)", 
                                       values=('✅ Instalado', pkg_name),
                                       tags=('installed',))
            else:
                item = self.tree.insert('', 'end', text=f"{module} (opcional)", 
                                       values=('⚠️ Faltante', pkg_name),
                                       tags=('optional',))
                self.optional_missing.append(package)
        
        # Configurar colores
        self.tree.tag_configure('installed', foreground='green')
        self.tree.tag_configure('missing', foreground='red')
        self.tree.tag_configure('optional', foreground='orange')
        
        # Actualizar botones
        if self.missing_deps:
            self.log_info(f"Dependencias faltantes: {', '.join(self.missing_deps)}")
            if "pyrtools" in self.missing_deps:
                self.log_info("⚠️ IMPORTANTE: pyrtools es OBLIGATORIO para la GUI completa")
            self.full_button.config(state='disabled')
        else:
            self.log_info("✅ Todas las dependencias principales están instaladas!")
            self.log_info("✅ pyrtools está disponible - GUI completa lista para usar")
            self.install_button.config(state='disabled')
            
        if self.optional_missing:
            self.log_info(f"Dependencias opcionales faltantes: {', '.join(self.optional_missing)}")
            
    def install_missing(self):
        """Instalar dependencias faltantes"""
        if not self.missing_deps:
            messagebox.showinfo("Info", "No hay dependencias faltantes que instalar.")
            return
            
        self.log_info("Instalando dependencias faltantes...")
        self.install_button.config(state='disabled', text='Instalando...')
        
        failed_installs = []
        
        for package in self.missing_deps:
            self.log_info(f"Instalando {package}...")
            if install_package(package):
                self.log_info(f"✅ {package} instalado correctamente")
            else:
                self.log_info(f"❌ Error instalando {package}")
                failed_installs.append(package)
        
        if failed_installs:
            messagebox.showerror("Error", 
                               f"No se pudieron instalar: {', '.join(failed_installs)}\n"
                               "Instálalos manualmente con: pip install <paquete>")
        else:
            messagebox.showinfo("Éxito", "Todas las dependencias se instalaron correctamente!")
            
        # Volver a verificar
        self.tree.delete(*self.tree.get_children())
        self.check_all_dependencies()
        
            
    def run_full_gui(self):
        """Ejecutar GUI completa"""
        if self.missing_deps:
            messagebox.showwarning("Advertencia", 
                                 "Hay dependencias faltantes. Instálalas primero.")
            return
            
        self.log_info("Ejecutando GUI completa...")
        try:
            subprocess.Popen([sys.executable, "motion_magnification_gui.py"])
            self.log_info("GUI completa iniciada en proceso separado.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo ejecutar la GUI:\n{str(e)}")

def main():
    """Función principal"""
    try:
        app = DependencyChecker()
        app.root.mainloop()
    except Exception as e:
        # Fallback en caso de que tkinter no esté disponible
        print(f"Error al iniciar el verificador de dependencias: {e}")
        print("Verificando dependencias desde línea de comandos...")
        
        dependencies = [
            ("cv2", "opencv-contrib-python"),
            ("numpy", "numpy"),
            ("matplotlib", "matplotlib"),
            ("scipy", "scipy"),
            ("skimage", "scikit-image"),
            ("PIL", "pillow"),
            ("pyrtools", "pyrtools"),
            ("pandas", "pandas"),
            ("fpdf", "fpdf")
        ]
        
        missing = []
        for module, package in dependencies:
            is_installed, _ = check_dependency(module, package)
            if is_installed:
                print(f"✅ {module} está instalado")
            else:
                print(f"❌ {module} NO está instalado (paquete: {package})")
                missing.append(package)
        
        if missing:
            print(f"\nPara instalar las dependencias faltantes, ejecuta:")
            print(f"pip install {' '.join(missing)}")
        else:
            print("✅ Todas las dependencias están instaladas!")

if __name__ == "__main__":
    main()
