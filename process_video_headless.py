"""Script mínimo para procesamiento headless (modo batch).

Este script realiza un procesamiento ligero de vídeo: calcula la media de
intensidad por frame dentro de una ROI (si se proporciona) y exporta los datos
a CSV usando `src.utils.export_signal_data`.

Es una implementación de bajo riesgo que permite ejecutar procesamiento sin GUI
para integración en pipelines o servidores.
"""
import argparse
import cv2
import os
from src import utils
from src import processing


def process_video(input_file, output_csv=None, roi=None, max_frames=None):
    cap = cv2.VideoCapture(input_file)
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir el archivo: {input_file}")

    signal = []
    times = []
    idx = 0

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    start_time = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Procesar frame con pipeline compartido
        params = {
            'roi': roi,
            'method': 'mean',
            'magnify_engine': None,
            'alpha': None,
            'lambda_c': None,
            'noise_reduction': False,
            'morphological_filtering': False
        }
        out = processing.process_frame(frame, params=params)
        mean_val = out['signal']
        signal.append(mean_val)
        times.append(idx / fps)

        idx += 1
        if max_frames and idx >= max_frames:
            break

    cap.release()

    if output_csv is None:
        base = os.path.splitext(os.path.basename(input_file))[0]
        output_csv = f"{base}_signal.csv"

    ok, fname = utils.export_signal_data(signal, times, filename=output_csv)
    if not ok:
        raise RuntimeError(f"Error exportando CSV: {fname}")

    return fname


def parse_roi(s: str):
    try:
        parts = [int(p) for p in s.split(',')]
        if len(parts) != 4:
            raise ValueError
        return tuple(parts)
    except Exception:
        raise argparse.ArgumentTypeError("ROI debe tener formato x,y,w,h con enteros")


def main():
    parser = argparse.ArgumentParser(description="Procesamiento headless de vídeo (exporta señal simple)")
    parser.add_argument('input', help='Archivo de vídeo a procesar')
    parser.add_argument('--output', '-o', help='Archivo CSV de salida', default=None)
    parser.add_argument('--roi', type=parse_roi, help='ROI en formato x,y,w,h', default=None)
    parser.add_argument('--max-frames', type=int, default=None, help='Número máximo de frames a procesar')

    args = parser.parse_args()

    out = process_video(args.input, output_csv=args.output, roi=args.roi, max_frames=args.max_frames)
    print(f"Procesamiento completado. CSV generado: {out}")


if __name__ == '__main__':
    main()
