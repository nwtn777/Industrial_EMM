import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import csv
import os

class VibrationAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Vibration FFT Analyzer")
        self.root.geometry("900x700")
        
        self.file_path = None
        self.signal_data = None
        
        self.create_widgets()
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # File selection section
        file_frame = ttk.LabelFrame(main_frame, text="File Selection", padding="10")
        file_frame.pack(fill=tk.X, pady=5)
        
        self.file_label = ttk.Label(file_frame, text="No file selected", width=50)
        self.file_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Button(file_frame, text="Browse", command=self.browse_file).pack(side=tk.RIGHT, padx=5)
        
        # Parameters section
        param_frame = ttk.LabelFrame(main_frame, text="Analysis Parameters", padding="10")
        param_frame.pack(fill=tk.X, pady=5)
        
        # Sampling frequency
        ttk.Label(param_frame, text="Sampling Frequency (Hz):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.fs_var = tk.StringVar(value="20")
        ttk.Entry(param_frame, textvariable=self.fs_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Cut-off time
        ttk.Label(param_frame, text="Cut-off Time (s):").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.cutoff_var = tk.StringVar(value="45")
        ttk.Entry(param_frame, textvariable=self.cutoff_var, width=10).grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        
        # Max frequency to display
        ttk.Label(param_frame, text="Max Freq. to Display (Hz):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.max_freq_var = tk.StringVar(value="5")
        ttk.Entry(param_frame, textvariable=self.max_freq_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Column selection
        ttk.Label(param_frame, text="Data Column:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        self.column_var = tk.StringVar(value="2")
        ttk.Entry(param_frame, textvariable=self.column_var, width=10).grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)
        
        # NEW: Low Frequency Filter
        filter_frame = ttk.LabelFrame(main_frame, text="Frequency Filtering", padding="10")
        filter_frame.pack(fill=tk.X, pady=5)
        
        # High-pass filter checkbox
        self.highpass_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(filter_frame, text="Enable High-pass Filter", 
                        variable=self.highpass_enabled).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        # High-pass cutoff frequency
        ttk.Label(filter_frame, text="High-pass Cutoff (Hz):").grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        self.highpass_cutoff = tk.StringVar(value="0.5")
        ttk.Entry(filter_frame, textvariable=self.highpass_cutoff, width=10).grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        
        # Filter description
        ttk.Label(filter_frame, text="(Removes DC offset, drift, and low-frequency noise)").grid(
            row=0, column=3, sticky=tk.W, padx=5, pady=5)
        
        # Analyze button
        ttk.Button(filter_frame, text="Analyze", command=self.analyze_signal).grid(row=0, column=4, padx=20, pady=5)
        
        # Plot area
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(8, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=main_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Vibration Data File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            self.file_path = file_path
            self.file_label.config(text=os.path.basename(file_path))
            self.status_var.set(f"File loaded: {os.path.basename(file_path)}")
    
    def analyze_signal(self):
        if not self.file_path:
            messagebox.showerror("Error", "Please select a file first.")
            return
            
        try:
            # Get parameters
            fs = float(self.fs_var.get())
            cutoff_time = float(self.cutoff_var.get())
            max_freq = float(self.max_freq_var.get())
            column_idx = int(self.column_var.get())
            
            # Get filter parameters
            highpass_enabled = self.highpass_enabled.get()
            if highpass_enabled:
                try:
                    highpass_cutoff = float(self.highpass_cutoff.get())
                    if highpass_cutoff < 0:
                        messagebox.showerror("Error", "High-pass cutoff frequency must be positive.")
                        return
                except ValueError:
                    messagebox.showerror("Error", "Invalid high-pass cutoff frequency.")
                    return
            
            # Load data
            with open(self.file_path, newline='') as f:
                reader = csv.reader(f)
                data = list(reader)
            
            # Extract signal
            try:
                signal_array = np.array([float(row[column_idx]) for row in data[1:]])
            except (IndexError, ValueError):
                messagebox.showerror("Error", f"Could not read column {column_idx} from the data file.")
                return
                
            # Cut signal to eliminate transient
            muestras_corte = int(cutoff_time * fs)
            if muestras_corte >= len(signal_array):
                messagebox.showerror("Error", "Cut-off time exceeds signal length.")
                return
                
            signal_array_cortada = signal_array[muestras_corte:]
            N = len(signal_array_cortada)
            
            # FFT calculation
            X = np.fft.fft(signal_array_cortada)
            
            # Apply high-pass filter if enabled
            if highpass_enabled:
                # Calculate the bin index corresponding to the cutoff frequency
                bin_cutoff = int(np.ceil(highpass_cutoff * N / fs))
                
                # Zero out frequencies below the cutoff (and corresponding negative frequencies)
                if bin_cutoff > 0:
                    X[:bin_cutoff] = 0
                    X[N-bin_cutoff+1:] = 0  # Symmetric negative frequencies
                    
                self.status_var.set(f"Analysis complete with high-pass filter at {highpass_cutoff} Hz")
            
            # Calculate magnitude spectrum
            X_mag = np.abs(X) / N
            X_mag_plot = 2 * X_mag[:N//2+1]
            X_mag_plot[0] = X_mag_plot[0] / 2  # Correct DC component
            
            # Frequency axis
            f_plot = np.linspace(0, fs/2, N//2+1)
            
            # Reconstruct filtered time domain signal if needed
            if highpass_enabled:
                signal_filtered = np.real(np.fft.ifft(X))
            else:
                signal_filtered = signal_array_cortada
            
            # Clear previous plots
            self.ax1.clear()
            self.ax2.clear()
            
            # Plot time domain
            self.ax1.plot(
                np.arange(len(signal_filtered)) / fs + cutoff_time,
                signal_filtered,
                'b'
            )
            title_suffix = " (High-pass Filtered)" if highpass_enabled else " (after cut-off)"
            self.ax1.set_title('Signal' + title_suffix)
            self.ax1.set_ylabel('Amplitude')
            self.ax1.set_xlabel('Time (s)')
            self.ax1.grid(True)
            
            # Plot frequency domain
            self.ax2.plot(f_plot, X_mag_plot, 'r')
            self.ax2.set_title('FFT Magnitude' + title_suffix)
            self.ax2.set_ylabel('Magnitude')
            self.ax2.set_xlabel('Frequency (Hz)')
            self.ax2.set_xlim(-0.1, max_freq)  # Configurable max frequency display
            self.ax2.set_ylim(0, np.max(X_mag_plot) * 1.1)
            self.ax2.grid(True)
            
            # If high-pass filter is enabled, mark the cutoff frequency
            if highpass_enabled:
                self.ax2.axvline(x=highpass_cutoff, color='g', linestyle='--', 
                                label=f'Cutoff: {highpass_cutoff} Hz')
                self.ax2.legend()
            
            self.fig.tight_layout()
            self.canvas.draw()
            
            if not highpass_enabled:
                self.status_var.set("Analysis complete")
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during analysis: {str(e)}")
            self.status_var.set("Error during analysis")
            
if __name__ == "__main__":
    root = tk.Tk()
    app = VibrationAnalyzerApp(root)
    root.mainloop()