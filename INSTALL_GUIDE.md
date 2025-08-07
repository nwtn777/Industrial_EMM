# Motion Magnification GUI - Instalación y Uso

## 🚀 Instalación Rápida

### Opción 1: Instalación Automática (Windows)
1. Ejecuta `run_gui.bat`
2. Selecciona la opción 4 para instalar dependencias
3. Luego selecciona la opción 1 para el launcher

### Opción 2: Instalación Manual
```bash
# Instalar dependencias
pip install -r requirements_gui.txt

# Ejecutar verificador de dependencias
python launcher.py

# O ejecutar directamente
python motion_magnification_gui.py
```

## 📁 Estructura del Proyecto

```
motion_magnification/
├── 📄 motion_magnification_gui.py    # GUI principal completa
├── 📄 demo_gui.py                    # Demo simplificado
├── 📄 launcher.py                    # Verificador de dependencias
├── 📄 utils.py                       # Utilidades y configuración
├── 📄 config.json                    # Archivo de configuración
├── 📄 run_gui.bat                    # Launcher para Windows
├── 📄 requirements_gui.txt           # Dependencias para GUI
├── 📄 README_GUI.md                  # Documentación detallada
├── 📄 INSTALL_GUIDE.md              # Esta guía
└── 📁 historiales/                   # Archivos CSV generados
```

## 🎯 Archivos Principales

### `motion_magnification_gui.py`
- **Propósito**: Aplicación GUI completa con todas las funcionalidades
- **Características**: Control de cámara, ROI, auto-tune, gráficas en tiempo real
- **Dependencias**: Todas las librerías (pyrtools es OBLIGATORIO)

### `demo_gui.py`
- **Propósito**: Demo simplificado sin dependencias complejas
- **Características**: Interfaz GUI básica con datos simulados
- **Dependencias**: Solo tkinter, matplotlib, numpy

### `launcher.py`
- **Propósito**: Verificador de dependencias y launcher inteligente
- **Características**: Detecta paquetes faltantes, ofrece instalación automática
- **Dependencias**: Solo tkinter

## 🔧 Configuración

El archivo `config.json` permite personalizar:

```json
{
    "default_settings": {
        "camera_id": 0,           // Cámara por defecto
        "fps": 10.0,              // FPS por defecto
        "alpha": 200.0,           // Factor de magnificación
        "lambda_c": 120.0,        // Parámetro lambda
        "fl": 0.07,               // Frecuencia baja
        "fh": 3.0                 // Frecuencia alta
    }
}
```

## 🚨 Solución de Problemas

### Error: "pyrtools es una dependencia obligatoria"
**Solución**: 
1. Instala pyrtools automáticamente: `python launcher.py`
2. O instala manualmente:
   ```bash
   pip install pyrtools
   ```
3. Si falla la instalación estándar, prueba desde GitHub:
   ```bash
   pip install https://github.com/LabForComputationalVision/pyrtools/archive/main.zip
   ```
4. **Nota**: pyrtools es OBLIGATORIO para la GUI completa. Para pruebas sin pyrtools, usa `python demo_gui.py`

### Error: "No se puede abrir la cámara"
**Solución**:
1. Verifica que la cámara esté conectada
2. Cierra otras aplicaciones que usen la cámara
3. Prueba diferentes índices de cámara (0, 1, 2...)

### Error: "Tkinter no disponible"
**Solución**:
- **Windows**: Reinstala Python desde python.org
- **Linux**: `sudo apt-get install python3-tk`
- **macOS**: `brew install python-tk`

### Rendimiento lento
**Solución**:
1. Reduce FPS en la configuración
2. Selecciona un ROI más pequeño
3. Cierra otras aplicaciones pesadas

## 📊 Funcionalidades por Archivo

| Funcionalidad | GUI Completa | Demo | Launcher |
|---------------|--------------|------|----------|
| Selección de cámara | ✅ | ✅ | ➖ |
| Control de parámetros | ✅ | ✅ | ➖ |
| ROI interactivo | ✅ | ➖ | ➖ |
| Magnificación real | ✅ | ➖ | ➖ |
| Gráficas tiempo real | ✅ | ✅ | ➖ |
| Auto-tune frecuencias | ✅ | ➖ | ➖ |
| Guardado CSV | ✅ | ➖ | ➖ |
| Verificación deps | ➖ | ➖ | ✅ |

## 🎮 Uso Paso a Paso

### Para Principiantes (Demo)
1. Ejecuta `python demo_gui.py`
2. Selecciona cámara y FPS
3. Haz clic en "Iniciar Demo"
4. Observa la gráfica simulada

### Para Uso Completo
1. Ejecuta `python launcher.py`
2. Instala dependencias faltantes si las hay
3. Ejecuta GUI completa
4. Configura parámetros
5. Selecciona ROI en la imagen
6. Inicia monitoreo

## 📈 Interpretación de Resultados

### Gráfica de Señal
- **Eje X**: Tiempo (frames o segundos)
- **Eje Y**: Intensidad de la señal
- **Interpretación**: Variaciones indican movimiento/vibración

### Gráfica FFT
- **Eje X**: Frecuencia (Hz)
- **Eje Y**: Magnitud
- **Interpretación**: Picos indican frecuencias dominantes

### Archivos CSV
- **Columnas**: frame, timestamp, mean_magnitude, mean_signal
- **Uso**: Análisis posterior, reportes, comparaciones

## 🔄 Flujo de Trabajo Recomendado

1. **Preparación**
   - Ejecutar `launcher.py` para verificar dependencias
   - Configurar cámara y iluminación

2. **Configuración Inicial**
   - Abrir GUI completa
   - Seleccionar cámara apropiada
   - Ajustar FPS según capacidad del sistema

3. **Selección de ROI**
   - Enfocar la zona de interés
   - Dibujar ROI sobre el área a monitorear
   - Verificar que capture el movimiento deseado

4. **Optimización**
   - Usar auto-tune para optimizar frecuencias
   - Ajustar alpha según la magnificación deseada
   - Monitorear rendimiento en tiempo real

5. **Monitoreo**
   - Observar gráficas en tiempo real
   - Revisar consola para mensajes importantes
   - Guardar datos para análisis posterior

## 🎯 Consejos de Rendimiento

- **FPS**: Comienza con 10 FPS, ajusta según rendimiento
- **ROI**: Mantén el ROI tan pequeño como sea posible
- **Alpha**: Valores altos (>500) pueden causar artefactos
- **Iluminación**: Mantén iluminación constante para mejores resultados

## 📝 Notas Importantes

- Los archivos CSV se guardan automáticamente en `historiales/`
- La configuración se puede modificar en tiempo real
- El sistema funciona mejor con movimientos periódicos
- Para análisis científico, usa frecuencias de muestreo apropiadas
