import cv2
import scipy.signal as signal
import scipy.fftpack as fftpack
from skimage import img_as_float, img_as_ubyte
import numpy as np
import time
import pyrtools as pt
import copy
import concurrent.futures
import matplotlib.pyplot as plt
from collections import deque
import csv
import datetime
import os

def draw_flow(img, flow, step=16):
    """Dibuja el flujo óptico sobre la imagen."""
    h, w = img.shape[:2]
    y, x = np.mgrid[step/2:h:step, step/2:w:step].reshape(2,-1).astype(int)
    fx, fy = flow[y,x].T
    lines = np.vstack([x, y, x+fx, y+fy]).T.reshape(-1, 2, 2)
    lines = np.int32(lines + 0.5)
    vis = img.copy()
    cv2.polylines(vis, lines, 0, (0, 255, 0))
    for (x1, y1), (_x2, _y2) in lines:
        cv2.circle(vis, (x1, y1), 1, (0, 255, 0), -1)
    magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    cv2.putText(vis, "magnitud_prom: " + str(np.mean(magnitude)) + "px/f", [50,450], 1, 2, (0, 0, 255))
    return vis

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

def process_frame(final_img, prev_gray, mask, s):
    """Procesa un frame y retorna los resultados de magnificación y flujo óptico."""
    gray = cv2.cvtColor(final_img, cv2.COLOR_BGR2GRAY)
    out = s.Magnify(gray)
    flow = cv2.calcOpticalFlowFarneback(prev_gray, out, None, 0.5, 3, 15, 3, 5, 1.2, 0)
    magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    mask[..., 0] = angle * 180 / np.pi / 2
    mask[..., 2] = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX)
    rgb = cv2.cvtColor(mask, cv2.COLOR_HSV2BGR)
    mag_fft_shift = np.fft.fftshift(np.abs(np.fft.fftshift(magnitude)))
    return out, flow, final_img, rgb, mag_fft_shift, gray

def seleccionar_roi(frame):
    """Permite al usuario seleccionar el ROI en la imagen."""
    roi = cv2.selectROI("Selecciona ROI", frame, fromCenter=False, showCrosshair=True)
    cv2.destroyWindow("Selecciona ROI")
    x, y, w_roi, h_roi = roi
    return x, y, w_roi, h_roi

def auto_tune_fl_fh(signal_buffer, fps):
    """
    Ajusta automáticamente fl y fh usando los picos del espectro de la señal.
    Usa scipy.signal.find_peaks para una detección robusta.
    """
    from scipy.signal import find_peaks
    signal_arr = np.array(signal_buffer) - np.mean(signal_buffer)
    fft_vals = np.abs(np.fft.rfft(signal_arr))
    freqs = np.fft.rfftfreq(len(signal_arr), d=1.0/fps)
    peaks, _ = find_peaks(fft_vals[1:], height=np.max(fft_vals[1:]) * 0.2)  # 20% del máximo
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

if __name__ == "__main__":
    fps = 10
    alpha = 200
    lambda_c = 120
    fl = 0.07
    fh = 3
    selec_cam = 0

    cam = cv2.VideoCapture(selec_cam)
    try:
        ret, img1 = cam.read()
        if not ret or img1 is None:
            print("Error: Could not read from camera.")
            exit(1)

        x, y, w_roi, h_roi = seleccionar_roi(img1)
        roi = (x, y, w_roi, h_roi)
        cv2.rectangle(img1, (x, y), (x + w_roi, y + h_roi), (255, 0, 0), 2)
        cv2.imshow("ROI Maquinaria", img1)
        cv2.waitKey(1000)
        cv2.destroyWindow("ROI Maquinaria")

        # --------- Buffer para autoajuste de fl y fh ---------
        buffer_size = min(100, fps * 5)  # ~5 segundos o 100 frames
        auto_buffer = []
        print("Recolectando señal para autoajuste de fl y fh...")
        for _ in range(buffer_size):
            ret, frame = cam.read()
            if not ret or frame is None:
                print("Error: Could not read from camera.")
                exit(1)
            roi_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)[y:y+h_roi, x:x+w_roi]
            roi_gray = cv2.GaussianBlur(roi_gray, (5, 5), 0)
            mean_signal = np.mean(roi_gray)
            auto_buffer.append(mean_signal)
            cv2.imshow("Recolectando señal...", frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break
        cv2.destroyWindow("Recolectando señal...")

        # Auto-tune fl y fh
        fl, fh = auto_tune_fl_fh(auto_buffer, fps)
        print(f"Autoajuste: fl={fl:.3f}, fh={fh:.3f}")

        gray = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        roi_gray = gray[y:y+h_roi, x:x+w_roi]
        roi_gray = cv2.GaussianBlur(roi_gray, (5, 5), 0)
        s = Magnify(roi_gray, alpha, lambda_c, fl, fh, fps)
        prev_gray = gray

        signal_buffer = deque(maxlen=300)
        plt.ion()
        fig, ax = plt.subplots()
        (line,) = ax.plot([], [])
        ax.set_ylim(0, 255)
        ax.set_xlim(0, 300)
        ax.set_title("Vibration Signal (ROI)")
        ax.set_xlabel("Frame")
        ax.set_ylabel("Mean Intensity")

        # Crear carpeta para históricos si no existe
        output_dir = "historiales"
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = os.path.join(output_dir, f"vibration_history_{timestamp}.csv")
        csv_file = open(csv_filename, mode='w', newline='')
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["frame", "timestamp", "mean_magnitude"])
        frame_count = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            while True:
                t1 = time.perf_counter()
                ret, final_img = cam.read()
                if not ret or final_img is None:
                    print("Error: Could not read from camera.")
                    break

                roi_img = final_img[y:y+h_roi, x:x+w_roi]
                mask = np.zeros_like(roi_img)
                mask[..., 1] = 255
                future = executor.submit(process_frame, roi_img, prev_gray[y:y+h_roi, x:x+w_roi], mask, s)
                out, flow, _, rgb, mag_fft_shift, roi_gray = future.result()

                # Mostrar ROI magnificado en la imagen original
                final_img[y:y+h_roi, x:x+w_roi] = cv2.cvtColor(out, cv2.COLOR_GRAY2BGR)
                cv2.rectangle(final_img, (x, y), (x+w_roi, y+h_roi), (255, 0, 0), 2)
                cv2.imshow('Vibration Monitoring', final_img)

                # Guardar datos en el archivo CSV (solo una vez por frame)
                mean_magnitude = np.mean(cv2.norm(flow, cv2.NORM_L2))
                timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                csv_writer.writerow([frame_count, timestamp_str, mean_magnitude])

                key = cv2.waitKey(1) & 0xFF
                if key == 27:  # ESC para salir
                    break
                elif key == ord('r'):  # Presiona 'r' para re-seleccionar el ROI
                    x, y, w_roi, h_roi = seleccionar_roi(final_img)
                    roi_gray = cv2.cvtColor(final_img, cv2.COLOR_BGR2GRAY)[y:y+h_roi, x:x+w_roi]
                    # Re-autoajustar fl y fh si se desea aquí
                    s = Magnify(roi_gray, alpha, lambda_c, fl, fh, fps)
                    prev_gray = cv2.cvtColor(final_img, cv2.COLOR_BGR2GRAY)

                # Actualizar y mostrar la señal de vibración
                mean_signal = np.mean(out)
                signal_buffer.append(mean_signal)
                frame_count += 1

                line.set_ydata(signal_buffer)
                line.set_xdata(np.arange(len(signal_buffer)))
                ax.set_xlim(0, max(300, len(signal_buffer)))
                ax.set_ylim(min(signal_buffer, default=0), max(signal_buffer, default=255))
                fig.canvas.draw()
                fig.canvas.flush_events()

                t2 = time.perf_counter()


                # print("set fps", 1. / (t2 - t1))
                # prev_gray[y:y+h_roi, x:x+w_roi] = roi_gray
                # if t2 - t1 > 1. / fps:
                #     print("delayed")
    finally:
        cam.release()
        cv2.destroyAllWindows()
        try:
            csv_file.close()
        except:
            pass