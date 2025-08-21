import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import os

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
    for col in df.select_dtypes(include='number').columns:
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
    return image_paths

def generar_pdf(stats, image_paths, output_pdf):
    pdf = PDF()
    pdf.add_page()
    pdf.chapter_title('Estadísticas básicas:')
    body = stats.to_string()
    pdf.chapter_body(body)
    for img in image_paths:
        pdf.add_image(img)
    pdf.output(output_pdf)

def procesar_archivo(csv_path):
    df = pd.read_csv(csv_path)
    stats = calcular_estadisticas(df)
    output_dir = os.path.dirname(csv_path)
    base_filename = os.path.splitext(os.path.basename(csv_path))[0]
    image_paths = generar_graficos(df, output_dir, base_filename)
    output_pdf = os.path.join(output_dir, f'{base_filename}_reporte.pdf')
    generar_pdf(stats, image_paths, output_pdf)
    for img in image_paths:
        os.remove(img)
    return output_pdf

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
