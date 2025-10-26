"""Módulo de procesamiento compartido para Motion Magnification.

Contiene funciones reutilizables para:
- aplicar ROI
- calcular una señal simple por frame
- envolver el motor de magnificación (si está disponible)
- optimizar alpha/lambda usando el motor

La intención es mantener este módulo de bajo acoplamiento para que la GUI y
el modo headless puedan usar exactamente la misma lógica de procesamiento.
"""
from typing import Optional, Tuple, Sequence, List, Dict
import numpy as np
import cv2
from src import logger


def apply_roi(frame: np.ndarray, roi: Optional[Tuple[int, int, int, int]]):
    """Devuelve la subimagen definida por roi o la imagen completa si roi es None."""
    if roi is None:
        return frame
    x, y, w, h = roi
    return frame[y:y+h, x:x+w]


def compute_frame_signal(frame: np.ndarray, method: str = 'mean') -> float:
    """Calcula una medida de señal a partir de un frame.

    Actualmente soporta:
    - 'mean' o 'brightness': media de intensidad en escala de grises

    Se deja la puerta abierta para medidas más complejas (RMS, energía, banda
    específica, etc.).
    """
    if frame is None:
        return 0.0

    # Aceptar BGR o grayscale
    if frame.ndim == 3:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        gray = frame

    if method in ('mean', 'brightness'):
        return float(np.mean(gray))

    raise ValueError(f"Método de señal desconocido: {method}")


def magnify_frame(magnify_engine, gray_frame: np.ndarray, alpha: float, lambda_c: float) -> np.ndarray:
    """Aplica el motor de magnificación si está disponible.

    - Si magnify_engine es None, devuelve la misma imagen (sin procesar).
    - Se asume que magnify_engine tiene un método `Magnify(img)` que opera sobre
      una imagen en escala de grises o float.
    """
    if magnify_engine is None:
        return gray_frame

    try:
        # Algunos motores esperan imágenes normalizadas
        img = gray_frame.astype(np.float32)
        result = magnify_engine.Magnify(img)
        # Asegurar tipo compatible
        return result.astype(gray_frame.dtype)
    except Exception as e:
        logger.error(f"Error en magnify_frame: {e}")
        return gray_frame


def optimize_alpha_lambda(
    frame: np.ndarray,
    roi: Tuple[int, int, int, int],
    magnify_engine,
    alpha_range: Optional[Sequence[float]] = None,
    lambda_range: Optional[Sequence[float]] = None,
    metric: str = 'energy'
) -> Dict:
    """Busca combinaciones de alpha/lambda que maximicen una métrica en la ROI.

    Retorna un diccionario con claves: best_alpha, best_lambda, best_metric, results
    donde results es una lista de dicts con 'alpha', 'lambda', 'metric'.
    """
    import numpy as np

    if alpha_range is None:
        alpha_range = np.linspace(50, 300, 6)
    if lambda_range is None:
        lambda_range = np.linspace(20, 120, 6)

    x, y, w, h = roi
    roi_img = frame[y:y+h, x:x+w]
    # Asegurar grayscale
    if roi_img.ndim == 3:
        gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = roi_img

    best_metric = -np.inf
    best_alpha = None
    best_lambda = None
    results: List[Dict] = []

    for alpha in alpha_range:
        for lambd in lambda_range:
            # Intentar aplicar motor
            magnified = magnify_frame(magnify_engine, gray, alpha, lambd)

            # Métrica básica: energía de la diferencia
            diff = cv2.absdiff(magnified, gray)
            energy = float(np.var(diff))
            results.append({'alpha': float(alpha), 'lambda': float(lambd), 'metric': energy})
            if energy > best_metric:
                best_metric = energy
                best_alpha = float(alpha)
                best_lambda = float(lambd)

    logger.info(f"optimize_alpha_lambda: best alpha={best_alpha}, lambda={best_lambda}, metric={best_metric}")
    return {
        'best_alpha': best_alpha,
        'best_lambda': best_lambda,
        'best_metric': best_metric,
        'results': results
    }


def process_frame(frame: np.ndarray, params: Optional[Dict] = None) -> Dict:
    """Procesa un frame según los parámetros y devuelve resultados.

    Parámetros admitidos en `params` (opcional):
    - roi: Tuple[x,y,w,h] o None
    - method: 'mean' u otro método para calcular la señal
    - magnify_engine: motor de magnificación o None
    - alpha: valor alpha para magnificación
    - lambda_c: valor lambda_c para magnificación
    - noise_reduction: bool o nivel (si >0 aplica GaussianBlur)
    - gaussian_kernel: tuple (kx, ky)
    - morphological_filtering: bool
    - background_model: imagen para sustracción de fondo (opcional)
    - frame_buffer: secuencia (list/deque) de frames para suavizado temporal (opcional)

    Retorna diccionario con claves:
    - 'processed_frame': ndarray (gris o magnificado)
    - 'signal': float
    - 'metadata': dict con parámetros usados
    """
    if params is None:
        params = {}

    roi = params.get('roi')
    method = params.get('method', 'mean')
    magnify_engine = params.get('magnify_engine')
    alpha = params.get('alpha', params.get('alpha', 200.0))
    lambda_c = params.get('lambda_c', params.get('lambda_c', 80.0))
    noise_reduction = params.get('noise_reduction', False)
    gaussian_kernel = params.get('gaussian_kernel', (3, 3))
    morphological = params.get('morphological_filtering', False)
    background_model = params.get('background_model')
    frame_buffer = params.get('frame_buffer')

    # Aplicar ROI
    sub = apply_roi(frame, roi)

    # Convertir a gris si es necesario
    if sub is None:
        raise ValueError("Frame inválido")

    if sub.ndim == 3:
        gray = cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
    else:
        gray = sub

    # Suavizado temporalsimple: si frame_buffer se proporciona, puede usarse fuera
    if frame_buffer is not None:
        try:
            from collections import deque

            # copiar contenido para no modificar externamente
            fb = deque(list(frame_buffer), maxlen=getattr(frame_buffer, 'maxlen', None))
            fb.append(gray.copy())
            # promedio simple
            stacked = np.stack(list(fb), axis=0).astype(np.float32)
            gray = np.mean(stacked, axis=0).astype(gray.dtype)
        except Exception:
            # Si falla, ignorar suavizado
            pass

    # Reducción de ruido
    if noise_reduction:
        try:
            kx, ky = gaussian_kernel
            # asegurar tamaños impares
            kx = int(kx) if int(kx) % 2 == 1 else int(kx) + 1
            ky = int(ky) if int(ky) % 2 == 1 else int(ky) + 1
            gray = cv2.GaussianBlur(gray, (kx, ky), 0)
        except Exception:
            pass

    # Sustracción de fondo simple
    if background_model is not None:
        try:
            bg = background_model
            if bg.shape == gray.shape:
                gray = cv2.absdiff(gray, bg)
        except Exception:
            pass

    # Filtrado morfológico
    if morphological:
        try:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            gray = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
        except Exception:
            pass

    # Aplicar magnificación si hay motor
    processed = magnify_frame(magnify_engine, gray, alpha, lambda_c)

    # Calcular señal
    signal_value = compute_frame_signal(processed, method=method)

    metadata = {
        'roi': roi,
        'method': method,
        'alpha': alpha,
        'lambda_c': lambda_c,
        'noise_reduction': bool(noise_reduction),
        'morphological_filtering': bool(morphological)
    }

    return {
        'processed_frame': processed,
        'signal': float(signal_value),
        'metadata': metadata
    }
