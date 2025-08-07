
# 🖥️ Motion Magnification GUI - Sistema Avanzado de Monitoreo de Vibraciones

## 📖 Descripción

**Motion Magnification GUI** es una aplicación de escritorio avanzada para el análisis y monitoreo de vibraciones industriales en tiempo real. Utiliza técnicas de magnificación de movimiento basadas en pirámides Laplacianas para detectar y amplificar movimientos sutiles imperceptibles al ojo humano, convirtiéndose en una herramienta esencial para mantenimiento predictivo y control de calidad en entornos industriales.

La interfaz gráfica moderna ahora está organizada en pestañas:
- **Pestaña 1:** Configuración de parámetros y consola de eventos.
- **Pestaña 2:** Video en tiempo real y gráficas de vibración/FFT.
En la pestaña de video y gráficas, el video se muestra a la izquierda y las gráficas a la derecha para una visualización más intuitiva.

## Características Principales

- Visualización de video en tiempo real con selección de ROI y datos superpuestos.
- Control interactivo de parámetros (FPS, Alpha, Lambda_c, fl, fh).
- Gráficas en vivo: señal de vibración y espectro FFT.
- Consola integrada para logs y eventos.
- Auto-tune de frecuencias y guardado automático de históricos.


## 🎯 **Aplicaciones Industriales**

- **Mantenimiento Predictivo**: Detección temprana de fallos en rodamientos, motores y maquinaria rotativa
- **Control de Calidad**: Monitoreo continuo de vibraciones en líneas de producción
- **Análisis Estructural**: Evaluación de integridad en estructuras y equipos críticos
- **Investigación y Desarrollo**: Análisis detallado de fenómenos vibratorios complejos
- **Diagnóstico de Equipos**: Identificación de patrones anómalos en tiempo real

## 🔧 **Tecnologías Clave**

- **Pirámides Laplacianas**: Algoritmo optimizado para magnificación de movimientos sutiles
- **Análisis FFT en Tiempo Real**: Procesamiento espectral instantáneo con `scipy.signal`
- **Threading Avanzado**: Procesamiento paralelo para máximo rendimiento
- **Interfaz Matplotlib Integrada**: Visualización profesional de datos en tiempo real

## 🚀 **Instalación y Configuración**

**⚠️ IMPORTANTE: pyrtools es una dependencia OBLIGATORIA para el funcionamiento completo**

### Instalación Automática (Recomendada)
```bash
python launcher.py
```
El launcher verificará automáticamente todas las dependencias y las instalará si es necesario.

### Instalación Manual
1. Instalar dependencias básicas:
```bash
pip install -r requirements_gui.txt
```

2. Verificar que pyrtools esté funcionando:
```bash
python src/check_pyrtools.py
```

3. Ejecutar la aplicación:
```bash
python src/motion_magnification_gui.py
```

### **Alternativas si pyrtools falla:**
- Instalar desde GitHub: `pip install https://github.com/LabForComputationalVision/pyrtools/archive/main.zip`
- Para pruebas básicas sin pyrtools: `python src/demo_gui.py`
- Usar conda: `conda install -c conda-forge pyrtools`

## Uso

### Inicio Rápido
1. **Seleccionar Cámara**: Elegir el índice de cámara deseado (generalmente 0 para la cámara principal)
2. **Configurar Parámetros**: Ajustar FPS, Alpha, Lambda_c según las necesidades
3. **Iniciar Monitoreo**: 
   - Opción 1: Hacer clic en "▶ Iniciar" para usar calibración de ruido (recomendado)
   - Opción 2: Hacer clic en "▶ Iniciar Sin Calibración" para omitir la calibración de ruido
4. **Seleccionar ROI**: Clic en "Seleccionar ROI" y dibujar un rectángulo sobre la zona a monitorear
5. **Auto-tune (Opcional)**: Usar "Auto-tune Freq" para optimización automática de filtros


### Pestañas de la Interfaz

- **Configuración y Consola:**
  - Configuración de todos los parámetros y controles principales
  - Consola de eventos y mensajes del sistema

- **Video y Gráficas:**
  - El video en tiempo real se muestra a la izquierda
  - Las gráficas (señal de vibración y FFT) se muestran a la derecha

Esta organización facilita el monitoreo y ajuste de parámetros sin perder de vista el análisis visual y gráfico.

## 📊 **Salida de Datos y Monitoreo**

### Archivos de Histórico
Los datos se guardan automáticamente en:
- **Ubicación**: `historiales/vibration_history_YYYYMMDD_HHMMSS.csv`
- **Contenido**: frame, timestamp, magnitud media, señal de vibración
- **Formato**: CSV compatible con Excel y herramientas de análisis

### Métricas en Tiempo Real
- **Magnitud de vibración**: Valor RMS de la señal detectada
- **Espectro de frecuencias**: Análisis FFT actualizado continuamente
- **Detección de picos**: Identificación automática de frecuencias dominantes
- **Tendencias temporales**: Evolución de la señal a lo largo del tiempo

## Controles de Teclado (en ventanas OpenCV)

- **ESC**: Salir del monitoreo
- **R**: Re-seleccionar ROI durante el monitoreo

## 🎚️ Calibración de Ruido con la Máquina Apagada

La calibración de ruido de fondo es una característica avanzada que permite al sistema detectar y filtrar automáticamente las señales de ruido estáticas presentes en el entorno cuando la máquina está apagada.

### ¿Cómo funciona?

1. **Captura de línea base**: El sistema registra varios frames con la máquina apagada para establecer un perfil de "ruido de fondo"
2. **Creación de modelo estadístico**: Calcula la media y desviación estándar de cada píxel en los frames capturados
3. **Filtrado en tiempo real**: Durante el monitoreo, resta automáticamente el ruido identificado de la señal

### Procedimiento de calibración:

1. **Asegúrate que la máquina está APAGADA**
2. En la pestaña "Configuración y Consola", localiza la sección "Calibración de Ruido de Fondo"
3. Establece la duración de la calibración (segundos) - recomendado: 5-10 segundos
4. Presiona "🔧 Calibrar Ruido"
5. Espera a que finalice la calibración (barra de progreso)
6. Ahora puedes **encender la máquina** y presionar "▶ Iniciar"

### Opciones disponibles:

- **Calibrar y usar**: El procedimiento recomendado - calibra con máquina apagada, luego inicia el monitoreo
- **Omitir calibración**: Usa "▶ Iniciar Sin Calibración" para saltar este paso si no es necesario
- **Activar/Desactivar**: Usa el checkbox "Usar calibración" para activar/desactivar el modelo de ruido

Esta función mejora significativamente la precisión de detección en entornos ruidosos, especialmente para detectar pequeñas vibraciones.

## Parámetros Técnicos

### Alpha (Factor de Magnificación)
- **Rango**: 1-1000
- **Típico**: 200
- **Efecto**: Mayor valor = mayor magnificación de movimientos

### FPS (Fotogramas por Segundo)
- **Rango**: 1-60
- **Típico**: 10
- **Efecto**: Velocidad de procesamiento y muestreo

### Lambda_c (Corte de Longitud de Onda)
- **Rango**: 1-500
- **Típico**: 120
- **Efecto**: Filtro espacial para diferentes escalas de movimiento

### Frecuencias (fl, fh)
- **fl (Baja)**: 0.01-10 Hz
- **fh (Alta)**: 0.1-20 Hz
- **Efecto**: Filtros temporales para aislar frecuencias de interés

### Uso del Botón Auto-tune
El botón **⚙️ Auto-tune** ajusta automáticamente los parámetros fl y fh analizando la señal del ROI seleccionado. Se recomienda usarlo en los siguientes casos:

- **Al iniciar un nuevo análisis**: Cuando acabas de seleccionar un ROI y no conoces las frecuencias de vibración dominantes.
- **Al cambiar de máquina o componente**: Diferentes equipos tienen distintos patrones de vibración y frecuencias características.
- **Cuando cambian las condiciones operativas**: Si la máquina modifica su velocidad, carga de trabajo o condiciones ambientales.
- **Si no ves resultados claros**: Cuando el análisis no muestra patrones definidos con los parámetros actuales.
- **Para buscar vibraciones específicas**: El auto-ajuste detecta las frecuencias dominantes, permitiéndote enfocarte en las más significativas.

Para usar esta función correctamente:
1. Inicia el monitoreo (botón "▶ Iniciar")
2. Selecciona un ROI (botón "🎯 Seleccionar ROI") 
3. Haz clic en "⚙️ Auto-tune"

El sistema recolectará datos durante unos segundos y optimizará automáticamente los parámetros fl y fh.

## Solución de Problemas

### Error: "No se pudo abrir la cámara"
- Verificar que la cámara esté conectada
- Probar con diferentes índices de cámara (0, 1, 2...)
- Cerrar otras aplicaciones que puedan estar usando la cámara

### Rendimiento Lento
- Reducir FPS
- Seleccionar un ROI más pequeño
- Reducir el valor de Alpha

### Gráficas no se actualizan
- Asegurar que se ha seleccionado un ROI válido
- Verificar que hay suficiente movimiento en la escena

### Ruido excesivo en la señal
- Realizar una calibración de ruido de fondo con la máquina apagada
- Aumentar el nivel de filtrado en la sección de Filtrado de Ruido
- Activar los filtros morfológicos y de suavizado temporal

## 🏗️ **Arquitectura y Rendimiento**

### Diseño Técnico
- **Framework GUI**: Tkinter con diseño modular y responsive
- **Motor Gráfico**: Matplotlib con backend TkAgg optimizado
- **Procesamiento Paralelo**: Threading para operaciones no bloqueantes
- **Comunicación Inter-thread**: Queue thread-safe para máxima estabilidad
- **Algoritmo Core**: Magnificación Euleriana basada en pirámides Laplacianas

### Optimizaciones de Rendimiento
- **Procesamiento concurrente**: Separación de captura, análisis y visualización
- **Buffer circular**: Gestión eficiente de memoria para datos en tiempo real
- **ROI adaptativo**: Procesamiento focalizado para reducir carga computacional
- **Auto-escalado**: Ajuste automático de parámetros según capacidad del sistema

## 🆚 **Ventajas sobre la Versión CLI**

| Característica | Versión CLI | Versión GUI |
|----------------|-------------|-------------|
| **Interfaz** | Línea de comandos | Interfaz gráfica intuitiva |
| **Visualización** | Ventanas separadas | Gráficas integradas |
| **Control** | Parámetros fijos | Ajuste dinámico en tiempo real |
| **Monitoreo** | Log en terminal | Consola integrada con timestamps |
| **Experiencia** | Técnica | Amigable para usuarios finales |
| **Threading** | Básico | Avanzado, no bloqueante |
| **Configuración** | Manual | Auto-tune inteligente |

# 📝 Funcionalidad de Grabación CSV - Documentación

## 🎯 Resumen de Cambios

Se han agregado controles de grabación manual al sistema de Motion Magnification GUI que permiten al usuario iniciar y detener la grabación de datos al archivo CSV de forma independiente del monitoreo general.

## 🔧 Nuevas Características

### 1. **Botones de Grabación**
- **🔴 Iniciar Grabación**: Comienza a escribir datos de vibración a un archivo CSV específico
- **⏺ Detener Grabación**: Detiene la grabación y cierra el archivo CSV

### 2. **Variables de Control**
```python
self.is_recording = False          # Estado de grabación activa/inactiva
self.csv_file = None              # Objeto archivo CSV abierto
self.csv_writer = None            # Escritor CSV
self.recording_filename = ""      # Nombre del archivo de grabación actual
```

### 3. **Indicador de Estado**
- Nueva etiqueta que muestra el estado actual de la grabación
- Muestra el nombre del archivo cuando está grabando activamente
- Colores: Verde (grabando), Naranja (detenida)

## 🔄 Funcionamiento

### Sistema Dual de CSV
El sistema ahora mantiene **dos tipos de archivos CSV**:

1. **CSV de Historial** (automático):
   - Se crea automáticamente al iniciar el monitoreo
   - Archivo: `historiales/vibration_history_YYYYMMDD_HHMMSS.csv`
   - Funciona continuamente mientras el sistema está corriendo

2. **CSV de Grabación** (manual):
   - Se crea solo cuando el usuario presiona "Iniciar Grabación"
   - Archivo: `historiales/vibration_recording_YYYYMMDD_HHMMSS.csv`
   - El usuario controla cuándo empieza y termina

### Flujo de Trabajo
1. **Iniciar Sistema**: Usuario presiona "▶ Iniciar" → se habilitan controles de grabación
2. **Seleccionar ROI**: Opcional, para análisis de vibración específico
3. **Iniciar Grabación**: Usuario presiona "🔴 Iniciar Grabación" → comienza a escribir CSV
4. **Detener Grabación**: Usuario presiona "⏺ Detener Grabación" → CSV se guarda y cierra
5. **Repetir**: Se puede iniciar/detener grabación múltiples veces durante una sesión

## 📊 Formato de Datos CSV

### Sin Calibración Física:
```csv
frame,timestamp,mean_magnitude_px_frame,mean_signal
1,2025-08-07 14:30:15,2.45,128.3
2,2025-08-07 14:30:16,2.67,129.1
```

### Con Calibración Física:
```csv
frame,timestamp,mean_magnitude_px_frame,velocity_mm_s,mean_signal,mm_per_pixel
1,2025-08-07 14:30:15,2.45,12.34,128.3,0.1
2,2025-08-07 14:30:16,2.67,13.45,129.1,0.1
```

## 🎮 Estados de los Botones

| Estado del Sistema | Iniciar Grabación | Detener Grabación |
|-------------------|-------------------|------------------|
| Sistema detenido  | Deshabilitado     | Deshabilitado    |
| Sistema corriendo | Habilitado        | Deshabilitado    |
| Grabando          | Deshabilitado     | Habilitado       |

## 🛡️ Características de Seguridad

1. **Auto-detención**: Si se detiene el monitoreo mientras se graba, la grabación se detiene automáticamente
2. **Manejo de errores**: Errores de escritura se registran en la consola sin interrumpir el sistema
3. **Flush inmediato**: Los datos se escriben inmediatamente al archivo para evitar pérdida
4. **Validación de estado**: Los botones solo se activan cuando es apropiado
5. **Modos de inicio**: Opción para iniciar con o sin calibración de ruido de fondo

## 📂 Ubicación de Archivos

Todos los archivos CSV se guardan en el directorio `historiales/`:
- **Historial automático**: `vibration_history_YYYYMMDD_HHMMSS.csv`
- **Grabación manual**: `vibration_recording_YYYYMMDD_HHMMSS.csv`

## 🚀 Casos de Uso

### 1. **Análisis Continuo**
- Dejar el sistema corriendo con historial automático
- Usar grabación manual solo para eventos específicos

### 2. **Grabación de Eventos**
- Iniciar grabación manual antes de un evento esperado
- Detener grabación después del evento
- Mantener archivos separados por evento

### 3. **Experimentos Controlados**
- Múltiples grabaciones durante una sesión
- Cada grabación corresponde a una condición experimental diferente

### 4. **Entorno Industrial con Ruido Ambiental**
- Utilizar la calibración de ruido de fondo con la máquina apagada
- Establecer el modelo de ruido base
- Iniciar monitoreo para detectar solo las vibraciones reales de la máquina

## ⚙️ Integración con Funciones Existentes

- ✅ Compatible con calibración física
- ✅ Compatible con selección de ROI
- ✅ Compatible con auto-tune de frecuencias
- ✅ Compatible con calibración de ruido de fondo
- ✅ Integrado con el sistema de logging
- ✅ Respeta todos los parámetros de configuración existentes

## 🔮 **Roadmap y Futuras Mejoras**

### Próximas Versiones
- [ ] **Vista previa integrada**: Video en tiempo real dentro de la GUI
- [ ] **Múltiples ROIs**: Monitoreo simultáneo de varias zonas
- [ ] **Alertas inteligentes**: Sistema de notificaciones por umbral
- [ ] **Exportación avanzada**: PDF reports y exportación de gráficas
- [ ] **Base de datos**: Almacenamiento histórico con SQLite
- [ ] **API REST**: Integración con sistemas SCADA/MES
- [ ] **Machine Learning**: Detección automática de anomalías
- [ ] **Conectividad IoT**: Integración con sensores externos

### Mejoras de UX
- [ ] Temas dark/light
- [ ] Configuración de layouts personalizables
- [ ] Análisis estadístico automático
- [ ] Calibración asistida por wizard
- [ ] Soporte para webcams IP

## 🤝 **Contribuciones y Desarrollo**

Este proyecto está abierto a contribuciones. Para desarrolladores interesados:

### Cómo Contribuir
1. Fork el proyecto
2. Crea una rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -m 'Agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📝 **Licencia y Contacto**

- **Licencia**: MIT License
- **Autor**: [@nwtn777](https://github.com/nwtn777)
- **Repositorio**: [motion_magnification](https://github.com/nwtn777/motion_magnification)

---

⭐ **Si encuentras útil este proyecto, considera darle una estrella en GitHub**

🔧 **¿Necesitas personalización para tu industria específica? ¡Contáctanos para soluciones empresariales!**
