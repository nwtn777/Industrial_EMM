import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import os
import numpy as np

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Reporte Estadístico de Señal', 0, 1, 'C')
        self.ln(5)

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 11)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(2)

    def chapter_body(self, body):
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 8, body)
        self.ln()

    def add_image(self, image_path, w=180):
        self.image(image_path, w=w)
        self.ln(5)

def calcular_estadisticas(df):
    stats = df.describe().T[['mean', 'std', 'min', '50%', 'max']]
    stats.rename(columns={'50%': 'median'}, inplace=True)
    return stats

def generar_graficos(df, output_dir, base_filename):
    image_paths = []
    fft_image_paths = []
    fft_peaks_dict = {}
    for col in df.select_dtypes(include='number').columns:
        # Gráfico de la señal
        plt.figure(figsize=(8, 3))
        plt.plot(df[col], label=col)
        plt.title(f'Señal: {col}')
        plt.xlabel('Índice')
        plt.ylabel('Valor')
        plt.legend()
        img_path = os.path.join(output_dir, f'{base_filename}_{col}_plot.png')
        plt.tight_layout()
        plt.savefig(img_path)
        plt.close()
        image_paths.append(img_path)

        # FFT y espectro
        x = df[col].values
        n = len(x)
        x = x - np.mean(x)
        fft_vals = np.fft.rfft(x)
        fft_freqs = np.fft.rfftfreq(n, d=1.0)  # d=1.0: asume frecuencia de muestreo 1 Hz
        fft_mags = np.abs(fft_vals)
        # Gráfico espectro
        plt.figure(figsize=(8, 3))
        plt.plot(fft_freqs, fft_mags, label=f'FFT {col}')
        plt.title(f'Espectro de Frecuencia (FFT): {col}')
        plt.xlabel('Frecuencia [Hz]')
        plt.ylabel('Magnitud')
        plt.legend()
        fft_img_path = os.path.join(output_dir, f'{base_filename}_{col}_fft.png')
        plt.tight_layout()
        plt.savefig(fft_img_path)
        plt.close()
        fft_image_paths.append(fft_img_path)

        # Frecuencias dominantes (3 picos principales, ignorando DC)
        if len(fft_mags) > 1:
            mags = fft_mags.copy()
            mags[0] = 0  # Ignorar DC
            peak_indices = mags.argsort()[-3:][::-1]
            peaks = [(fft_freqs[i], fft_mags[i]) for i in peak_indices]
            fft_peaks_dict[col] = peaks
        else:
            fft_peaks_dict[col] = []
    return image_paths, fft_image_paths, fft_peaks_dict

def generar_pdf(stats, image_paths, fft_image_paths, fft_peaks_dict, output_pdf):
    pdf = PDF()
    pdf.add_page()
    pdf.chapter_title('Estadísticas básicas:')
    body = stats.to_string()
    pdf.chapter_body(body)
    for img in image_paths:
        pdf.add_image(img)
    pdf.chapter_title('Análisis de Frecuencias (FFT):')
    for col, peaks in fft_peaks_dict.items():
        pdf.chapter_title(f'Frecuencias dominantes en {col}:')
        if peaks:
            peak_str = '\n'.join([f'Frecuencia: {f:.2f} Hz, Magnitud: {m:.2f}' for f, m in peaks])
        else:
            peak_str = 'No se detectaron picos significativos.'
        pdf.chapter_body(peak_str)
    for img in fft_image_paths:
        pdf.add_image(img)
    pdf.output(output_pdf)


def procesar_archivo(csv_path):
    """Genera un reporte PDF para un archivo CSV y retorna la ruta del PDF generado."""
    df = pd.read_csv(csv_path)
    stats = calcular_estadisticas(df)
    output_dir = os.path.dirname(csv_path)
    base_filename = os.path.splitext(os.path.basename(csv_path))[0]
    image_paths, fft_image_paths, fft_peaks_dict = generar_graficos(df, output_dir, base_filename)
    output_pdf = os.path.join(output_dir, f'{base_filename}_reporte.pdf')
    generar_pdf(stats, image_paths, fft_image_paths, fft_peaks_dict, output_pdf)
    for img in image_paths + fft_image_paths:
        os.remove(img)
    return output_pdf

def generar_reportes_para_archivos(file_paths):
    """Genera reportes PDF para una lista de archivos CSV. Devuelve lista de rutas de PDF generados."""
    reportes = []
    for path in file_paths:
        try:
            pdf_path = procesar_archivo(path)
            reportes.append(pdf_path)
        except Exception as e:
            print(f'Error procesando {path}: {e}')
    return reportes

def seleccionar_archivos():
    file_paths = filedialog.askopenfilenames(
        title='Selecciona uno o más archivos CSV',
        filetypes=[('Archivos CSV', '*.csv')]
    )
    if not file_paths:
        return
    reportes = []
    for path in file_paths:
        try:
            pdf_path = procesar_archivo(path)
            reportes.append(pdf_path)
        except Exception as e:
            messagebox.showerror('Error', f'Error procesando {path}: {e}')
    if reportes:
        messagebox.showinfo('Listo', f'Reportes generados:\n' + '\n'.join(reportes))


def main():
    root = tk.Tk()
    root.title('Generador de Reportes Estadísticos de Señal')
    root.geometry('400x150')
    btn = tk.Button(root, text='Seleccionar archivos CSV', command=seleccionar_archivos, font=('Arial', 12), width=30)
    btn.pack(pady=40)
    root.mainloop()


if __name__ == '__main__':
    main()
