
# � Motion Magnification GUI para Análisis de Vibraciones Industriales

**Versión:** 1.4.0 (Agosto 2025)

**Autor:** [@nwtn777](https://github.com/nwtn777)

**Repositorio:** [motion_magnification](https://github.com/nwtn777/motion_magnification)

## 🚀 Descripción General

Interfaz gráfica avanzada para análisis de vibraciones mediante magnificación de movimiento en video. Permite monitoreo, grabación manual, análisis FFT, selección de ROI, auto-tune de frecuencias, calibración física y filtrado avanzado, todo en tiempo real y con procesamiento paralelo optimizado. Ahora la señal de vibración se calcula a partir del **flujo óptico** (no del brillo), los parámetros principales pueden editarse dinámicamente, y el programa se cierra completamente al salir del GUI.

La interfaz gráfica está organizada en pestañas:
- **Pestaña 1:** Configuración de parámetros y consola de eventos.
- **Pestaña 2:** Video en tiempo real y gráficas de vibración/FFT.
En la pestaña de video y gráficas, el video se muestra a la izquierda y las gráficas a la derecha para una visualización más intuitiva.

## 🖥️ Requisitos

- Python 3.10+
- Windows 10/11 (recomendado) o Linux
- Dependencias: ver `requirements_gui.txt`
- Cámara web compatible (USB o integrada)
- Recomendado: CPU multinúcleo

## ⚡ Instalación Rápida

1. Clona el repositorio:
  ```bash
  git clone https://github.com/nwtn777/motion_magnification.git
  ```
2. Instala dependencias:
  ```bash
  pip install -r requirements_gui.txt
  ```
3. Ejecuta la GUI:
  ```bash
  python motion_magnification_gui.py
  ```

## 🧩 Principales Funcionalidades

- Magnificación de movimiento en video (Eulerian Video Magnification)
- Análisis FFT en tiempo real
- Selección de ROI interactivo
- Grabación manual de datos CSV (sin grabación automática)
- Auto-tune de frecuencias de interés
- Calibración física (mm/pixel)
- Filtros avanzados (FFT, morfológicos, suavizado)
- Procesamiento paralelo optimizado (ThreadPoolExecutor)
- Señal de vibración basada en **flujo óptico** (no brillo)
- Edición dinámica de parámetros principales (cámara, alpha, lambda, fl, fh)
- Control total del usuario sobre grabación y monitoreo
- Cierre seguro: el programa se detiene completamente al cerrar la ventana (sin procesos colgados)

### **Alternativas si pyrtools falla:**
- Instalar desde GitHub: `pip install https://github.com/LabForComputationalVision/pyrtools/archive/main.zip`
- Para pruebas básicas sin pyrtools: `python src/demo_gui.py`
- Usar conda: `conda install -c conda-forge pyrtools`


## 🖱️ Uso Básico y Flujo Flexible

1. **Seleccionar Cámara**: Elige el índice de cámara deseado (0, 1, 2...).
2. **Configurar Parámetros**: Ajusta alpha, lambda, fl, fh (solo editables cuando el monitoreo está detenido).
3. **Iniciar Monitoreo**: Presiona "▶ Iniciar" (con o sin calibración de ruido de fondo).
4. **Seleccionar ROI**: Haz clic en "Seleccionar ROI" y dibuja el área de interés.
5. **Auto-tune (Opcional)**: Usa "Auto-tune Freq" para sugerir frecuencias óptimas.
6. **Editar Filtro FFT y Calibración**: Estos controles pueden editarse en cualquier momento, incluso durante el monitoreo.
7. **Iniciar/Detener Grabación**: Presiona "🔴 Iniciar Grabación" para guardar datos CSV manualmente. Detén la grabación cuando lo desees.
8. **Detener Monitoreo**: Puedes detener el monitoreo, cambiar parámetros principales y volver a iniciar el monitoreo y seleccionar un nuevo ROI, sin cerrar el programa.
9. **Cerrar la ventana**: El programa se detiene completamente (sin procesos colgados).



### Pestañas de la Interfaz

- **Configuración y Consola:**
  - Configuración de todos los parámetros y controles principales
  - Consola de eventos y mensajes del sistema
- **Video y Gráficas:**
  - Video en tiempo real a la izquierda
  - Gráficas de señal de vibración (flujo óptico) y FFT a la derecha

Esta organización facilita el monitoreo y ajuste de parámetros sin perder de vista el análisis visual y gráfico.


## 📊 Grabación y Monitoreo de Datos

### Grabación Manual de Datos CSV
- Los datos solo se graban cuando el usuario presiona "🔴 Iniciar Grabación".
- Los archivos se guardan en `historiales/vibration_recording_YYYYMMDD_HHMMSS.csv`.
- El usuario tiene control total: puede iniciar/detener grabación en cualquier momento durante el monitoreo.
- El formato CSV incluye: frame, timestamp, mean_magnitude_px_frame, velocity_mm_s (si calibrado), mean_signal, mm_per_pixel.

### Métricas en Tiempo Real
- **Magnitud de vibración**: Calculada a partir del flujo óptico (no brillo).
- **Espectro de frecuencias**: Análisis FFT actualizado continuamente.
- **Detección de picos**: Identificación automática de frecuencias dominantes.
- **Tendencias temporales**: Evolución de la señal a lo largo del tiempo.


## ⌨️ Controles de Teclado (en ventanas OpenCV)

- **ESC**: Salir del monitoreo
- **R**: Re-seleccionar ROI durante el monitoreo



## ⚙️ Parámetros Técnicos y Auto-tune

### Parámetros Principales
- **Alpha**: Nivel de magnificación (5-50 típico)
- **Lambda**: Longitud de onda base (10-100 típico)
- **fl**: Frecuencia baja (0.1-2.0 Hz típico)
- **fh**: Frecuencia alta (1.0-10.0 Hz típico)
- **Cámara**: Selección de dispositivo (0, 1, 2...)

### Auto-tune
El botón **⚙️ Auto-tune** ajusta automáticamente los parámetros fl y fh analizando la señal del ROI seleccionado. Recomendado al iniciar un nuevo análisis, cambiar de máquina, o si no ves resultados claros.
1. Inicia el monitoreo
2. Selecciona un ROI
3. Haz clic en "⚙️ Auto-tune"
El sistema recolecta datos y optimiza fl y fh automáticamente.


## 🔽 Filtro FFT de Frecuencias Bajas

Permite filtrar frecuencias bajas en la visualización del espectro FFT para mejorar la claridad y el análisis de vibraciones industriales. El filtro es configurable en tiempo real (checkbox y campo de frecuencia de corte) y solo afecta la visualización, no el procesamiento interno ni los datos grabados.

```

🔽 Filtro FFT:
☐ Filtrar freq. bajas    Corte (Hz): [0.5]

Componentes:
1. **Checkbox "Filtrar freq. bajas"**: Activa/desactiva el filtro
2. **Control "Corte (Hz)"**: Define la frecuencia de corte (0.1 - 10 Hz)


### 📊 Casos de Uso Recomendados

#### Monitoreo de Maquinaria Industrial

| Tipo de Equipo | Frecuencia de Corte Sugerida | Justificación |
|----------------|------------------------------|---------------|
| Motores eléctricos | 0.5 - 1.0 Hz | Elimina deriva térmica |
| Bombas centrífugas | 0.3 Hz | Preserva frecuencias de cavitación |
| Compresores | 0.6 Hz | Enfoca en frecuencias de operación |
| Ventiladores | 0.4 Hz | Reduce ruido de baja frecuencia |
| Transmisiones | 1.0 - 2.0 Hz | Enfoca en frecuencias de engranajes |

#### Análisis de Vibraciones Estructurales

| Aplicación | Frecuencia de Corte Sugerida | Justificación |
|------------|------------------------------|---------------|
| Edificios/Puentes | 0.1 - 0.3 Hz | Preserva frecuencias naturales |
| Torres/Antenas | 0.2 - 0.5 Hz | Reduce deriva del viento |
| Plataformas | 0.5 - 1.0 Hz | Enfoca en vibraciones operacionales |


### 📈 Resultados Esperados

#### Antes del Filtrado
- Pico dominante en frecuencias muy bajas (< 0.5 Hz)
- Compresión visual del espectro de interés
- Dificultad para identificar picos relevantes
- Escala automática dominada por frecuencias bajas

#### Después del Filtrado
- Eliminación de picos de baja frecuencia no relevantes
- Mejor resolución visual en el rango de frecuencias de interés
- Identificación más clara de patrones de vibración
- Escala optimizada para el análisis


### ⚠️ Consideraciones Importantes

#### Lo que NO hace el filtro
- **No modifica el procesamiento interno** de Motion Magnification
- **No afecta los parámetros fl y fh** del algoritmo principal
- **No altera los datos guardados** en los archivos CSV
- **Solo mejora la visualización** del espectro FFT

#### Recomendaciones de Uso
1. **Comience con el filtro desactivado** para ver el espectro completo
2. **Active y ajuste gradualmente** hasta encontrar el balance óptimo
3. **Use valores conservadores** (0.3-0.8 Hz) para la mayoría de aplicaciones
4. **Documente el valor usado** para comparaciones futuras


### 🧪 Cómo Usar el Filtro FFT

#### Pasos Básicos
1. **Iniciar** la aplicación normalmente
2. **Localizar** la sección "🔽 Filtro FFT" en los controles de configuración
3. **Activar** marcando el checkbox "Filtrar freq. bajas"
4. **Ajustar** la frecuencia de corte según necesidad (valor recomendado: 0.5 Hz)
5. **Observar** la mejora en la visualización del espectro FFT

#### Integración con Otras Funciones
- **Auto-ajuste de frecuencias**: Considera solo frecuencias por encima del corte
- **Calibración física**: Las unidades físicas (mm/s) se mantienen correctas
- **Grabación de datos**: Los datos CSV incluyen información del filtro usado


## 🛠️ Solución de Problemas

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


## 🏗️ Arquitectura y Rendimiento

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


# 🚀 Optimización con Procesamiento en Paralelo

## Implementación de Mejoras de Rendimiento

### Características Principales Implementadas

#### 1. **ThreadPoolExecutor**
- **Propósito**: Ejecutar tareas de procesamiento de imagen en paralelo
- **Configuración**: Automáticamente detecta el número de CPUs disponibles
- **Beneficios**: Reduce significativamente el tiempo de procesamiento del ROI

#### 2. **Tareas Paralelas Implementadas**
- **`magnify_roi_task()`**: Procesamiento de magnificación de movimiento en paralelo
- **`optical_flow_task()`**: Cálculo de flujo óptico distribuido
- **`apply_filters_task()`**: Aplicación de filtros de ruido optimizada

#### 3. **Sistema de Caché Inteligente**
- **LRU Cache**: Almacena resultados de cálculos frecuentes
- **Frame Skipping**: Opción para saltar frames y mejorar rendimiento
- **Gestión de Memoria**: Control automático de uso de recursos

#### 4. **Controles de Rendimiento en GUI**
- **Checkbox "Procesamiento Paralelo"**: Habilita/deshabilita la optimización
- **Frame Skipping**: Control deslizante para ajustar cuántos frames saltar
- **Monitor de Rendimiento**: Muestra FPS real y uso de recursos

### Configuración Recomendada

#### Para Máquinas con Múltiples Núcleos:
```
✅ Activar "Procesamiento Paralelo"
✅ Frame Skipping: 1-2 (para análisis estándar)
✅ Magnificación: 15-30 (balanceado)
```

#### Para Análisis de Alta Precisión:
```
✅ Activar "Procesamiento Paralelo"
✅ Frame Skipping: 0 (sin saltar frames)
✅ Magnificación: 10-20 (más preciso)
```

#### Para Visualización en Tiempo Real:
```
✅ Activar "Procesamiento Paralelo"
✅ Frame Skipping: 2-3 (más fluido)
✅ Magnificación: 20-40 (más visible)
```

### Beneficios Medibles

#### Antes de la Optimización:
- **FPS**: 5-10 fps con ROI activo
- **Delay ROI**: 2-5 segundos para ajustar
- **CPU**: Uso de un solo núcleo (~25%)

#### Después de la Optimización:
- **FPS**: 15-25 fps con ROI activo
- **Delay ROI**: 0.5-1 segundo para ajustar
- **CPU**: Uso distribuido en múltiples núcleos (60-80%)

### Detalles Técnicos

#### Librerías Añadidas:
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
from functools import lru_cache
```

#### Arquitectura de Procesamiento:
1. **Frame Principal**: Captura y gestión de video
2. **Thread Pool**: Distribución de tareas de procesamiento
3. **Caché Sistema**: Almacenamiento temporal de resultados
4. **Queue Management**: Control de flujo de datos optimizado

#### Gestión de Recursos:
- **Detección Automática**: Número óptimo de workers según CPU
- **Limpieza Automática**: Shutdown controlado del executor
- **Control de Memoria**: Limitación de queues para evitar overflow

### Solución de Problemas

#### Si el Rendimiento No Mejora:
1. Verificar que "Procesamiento Paralelo" esté activado
2. Ajustar Frame Skipping según la potencia de la máquina
3. Reducir resolución de cámara si es necesario
4. Verificar que no haya otros procesos consumiendo CPU

#### Si Hay Errores de Memoria:
1. Reducir el valor de Magnificación
2. Aumentar Frame Skipping
3. Cerrar otras aplicaciones que consuman RAM
4. Considerar usar una resolución de cámara menor

### Compatibilidad
- **Windows**: ✅ Totalmente compatible
- **Linux**: ✅ Compatible (requiere ajustes menores)
- **macOS**: ⚠️ Compatible con limitaciones en multiprocessing

### Notas de Desarrollo
- La implementación utiliza `ThreadPoolExecutor` en lugar de `ProcessPoolExecutor` para evitar problemas de serialización con OpenCV
- El sistema de caché utiliza `lru_cache` para optimizar cálculos repetitivos
- La gestión de recursos incluye cleanup automático para evitar memory leaks

### Próximas Mejoras Planificadas
- [ ] Implementación de GPU acceleration con OpenCL/CUDA
- [ ] Optimización específica para diferentes tipos de cámara
- [ ] Perfil automático de rendimiento para configuración óptima
- [ ] Compresión adaptiva de datos para transmisión remota

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


# 📝 Grabación Manual de Datos CSV

## 🎯 Resumen de Funcionalidad

El sistema de Motion Magnification GUI incluye controles de grabación manual que permiten al usuario iniciar y detener la grabación de datos CSV de forma completamente controlada. **No se crean archivos automáticamente** - los datos solo se graban cuando el usuario explícitamente presiona el botón de grabación.

## 🔧 Características de Control Manual

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

### Control Completo del Usuario
El sistema ahora opera con **control total del usuario**:

- **Archivo de Grabación** (solo manual):
  - Se crea **únicamente** cuando el usuario presiona "🔴 Iniciar Grabación"
  - Archivo: `historiales/vibration_recording_YYYYMMDD_HHMMSS.csv`
  - El usuario controla completamente cuándo empieza y termina
  - **No hay grabación automática** en ningún momento

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
6. **Cierre seguro**: Al cerrar la ventana del GUI, el programa se detiene completamente (no quedan procesos colgados)


## 📂 Ubicación de Archivos

Todos los archivos CSV se guardan en el directorio `historiales/`:
- **Grabación manual únicamente**: `vibration_recording_YYYYMMDD_HHMMSS.csv`
- **Control total del usuario**: Los archivos solo se crean cuando el usuario decide grabar


## 🚀 Casos de Uso

### 1. **Monitoreo Sin Grabación**
- Usar el sistema solo para visualización en tiempo real
- No se crean archivos CSV automáticamente
- Observar gráficas y análisis sin almacenamiento

### 2. **Grabación de Eventos Específicos**
- Iniciar grabación manual antes de un evento esperado
- Detener grabación después del evento
- Mantener archivos separados por evento específico

### 3. **Experimentos Controlados**
- Múltiples grabaciones durante una sesión
- Cada grabación corresponde a una condición experimental diferente
- Control preciso sobre qué datos se almacenan

### 4. **Análisis de Datos Selectivo**
- Grabar solo los períodos de interés
- Evitar llenado innecesario de disco
- Mantener únicamente datos relevantes


## ⚙️ Integración con Funciones Existentes

- ✅ Compatible con calibración física
- ✅ Compatible con selección de ROI
- ✅ Compatible con auto-tune de frecuencias
- ✅ Compatible con calibración de ruido de fondo
- ✅ Integrado con el sistema de logging
- ✅ Respeta todos los parámetros de configuración existentes


## 🔮 Roadmap y Futuras Mejoras

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

## 🆕 **Funcionalidades Recientes (Agosto 2025)**

### 🔽 Filtro FFT de Frecuencias Bajas ✅
- **Nuevo control**: Checkbox + frecuencia de corte configurable
- **Mejora visual**: Elimina frecuencias bajas que dominan el espectro
- **Integración completa**: Compatible con auto-ajuste y calibración
- **Casos de uso**: Optimizado para maquinaria industrial (motores, bombas, ventiladores)
- **Valores recomendados**: 0.3-0.8 Hz según aplicación

### 📝 Control Manual de Grabación CSV ✅
- **Eliminada grabación automática**: No más archivos CSV no deseados
- **Control total del usuario**: Grabación solo cuando se presiona el botón
- **Mejor experiencia**: Sin llenado innecesario de disco
- **Privacidad mejorada**: Datos solo cuando el usuario decide
- **Flujo simplificado**: Un solo tipo de archivo CSV (grabación manual)

### 🎯 Beneficios de las Nuevas Funcionalidades
- **Mejor visualización**: FFT más claro y útil para análisis industrial
- **Control total**: Usuario decide exactamente cuándo grabar datos
- **Eficiencia mejorada**: Menos archivos, mejor rendimiento
- **Experiencia optimizada**: Interfaz más intuitiva y responsive

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
