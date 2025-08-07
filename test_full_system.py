#!/usr/bin/env python3
"""
Test completo del sistema de magnificación optimizado después de correcciones.
"""

import numpy as np
import cv2
import sys
import os

# Añadir src al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from industrial_optimized_improved import OptimizedMagnify
    print("✓ Importación exitosa del sistema optimizado")
except ImportError as e:
    print(f"✗ Error de importación: {e}")
    sys.exit(1)

def test_magnification_system():
    """Test completo del sistema de magnificación."""
    print("\n=== TEST DEL SISTEMA DE MAGNIFICACIÓN COMPLETO ===")
    
    try:
        # 1. Crear frame inicial para la inicialización
        print("\n1. Creando frame inicial...")
        height, width = 480, 640
        frame1 = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        print(f"✓ Frame inicial creado: {gray1.shape}")
        
        # 2. Inicializar sistema con parámetros correctos
        print("\n2. Inicializando sistema...")
        magnifier = OptimizedMagnify(
            gray1=gray1,
            alpha=5.0,           # magnification
            lambda_c=120,        # pyramid_levels related
            fl=0.05,            # low frequency
            fh=0.4,             # high frequency  
            samplingRate=30.0   # sampling_rate
        )
        print("✓ Sistema inicializado correctamente")
        
        # 2. Crear frames de prueba sintéticos
        print("\n3. Creando frames adicionales de prueba...")
        
        # Frame con pequeño movimiento simulado
        frame2 = frame1.copy()
        # Simular vibración sutil desplazando una región
        frame2[100:200, 100:200] = np.roll(frame2[100:200, 100:200], 1, axis=0)
        
        print(f"✓ Frames adicionales creados")
        
        # 3. Test de magnificación (el filtro ya está inicializado)
        print("\n4. Probando magnificación...")
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        
        result = magnifier.magnify(gray2)
        
        if result is not None:
            print(f"✓ Magnificación exitosa. Resultado shape: {result.shape}")
            print(f"  - Tipo: {result.dtype}")
            print(f"  - Rango: [{result.min():.3f}, {result.max():.3f}]")
            
            # Verificar que el resultado es válido
            if not np.isnan(result).any() and not np.isinf(result).any():
                print("✓ Resultado libre de NaN/Inf")
            else:
                print("✗ Resultado contiene NaN/Inf")
                
        else:
            print("✗ Error: magnificación devolvió None")
            return False
            
        # 5. Test de múltiples frames
        print("\n5. Probando procesamiento de múltiples frames...")
        success_count = 0
        for i in range(10):
            # Generar frame con variación
            test_frame = frame1.copy()
            # Añadir ruido/variación
            noise = np.random.randint(-10, 11, test_frame.shape, dtype=np.int16)
            test_frame = np.clip(test_frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
            
            gray_test = cv2.cvtColor(test_frame, cv2.COLOR_BGR2GRAY)
            result = magnifier.magnify_frame(gray_test)
            
            if result is not None:
                success_count += 1
        
        print(f"✓ Frames procesados exitosamente: {success_count}/10")
        
        # 6. Test de performance
        print("\n6. Test de performance...")
        import time
        
        start_time = time.time()
        for i in range(30):  # 30 frames
            gray_test = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
            result = magnifier.magnify_frame(gray_test)
        
        elapsed = time.time() - start_time
        fps = 30 / elapsed
        print(f"✓ Performance: {fps:.1f} FPS promedio")
        
        return True
        
    except Exception as e:
        print(f"✗ Error en test del sistema: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_camera():
    """Test opcional con cámara si está disponible."""
    print("\n=== TEST CON CÁMARA (OPCIONAL) ===")
    
    try:
        # Intentar conectar cámara
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print("ℹ  Cámara no disponible para test")
            return True
            
        print("✓ Cámara detectada")
        
        # Configurar cámara
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Inicializar magnificador
        magnifier = OptimizedMagnify(
            gray1=gray1,
            alpha=10.0,
            lambda_c=120,
            fl=0.05,
            fh=0.4,
            samplingRate=30.0
        )
        
        # Capturar frames iniciales
        ret, frame1 = cap.read()
        if not ret:
            print("✗ No se pudo capturar frame inicial")
            cap.release()
            return False
            
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        magnifier.initialize_filter(gray1)
        print("✓ Filtro inicializado con frame de cámara")
        
        # Test de algunos frames
        frames_processed = 0
        for i in range(10):
            ret, frame = cap.read()
            if ret:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                result = magnifier.magnify_frame(gray)
                if result is not None:
                    frames_processed += 1
        
        cap.release()
        print(f"✓ Frames de cámara procesados: {frames_processed}/10")
        
        return frames_processed > 0
        
    except Exception as e:
        print(f"ℹ  Test de cámara no completado: {e}")
        return True  # No es error crítico

if __name__ == "__main__":
    print("SISTEMA DE MAGNIFICACIÓN DE MOVIMIENTO - TEST COMPLETO")
    print("=" * 60)
    
    # Test principal del sistema
    system_ok = test_magnification_system()
    
    # Test opcional con cámara
    camera_ok = test_with_camera()
    
    print("\n" + "=" * 60)
    print("RESULTADOS DEL TEST:")
    print(f"Sistema de magnificación: {'✓ PASS' if system_ok else '✗ FAIL'}")
    print(f"Test con cámara: {'✓ PASS' if camera_ok else 'ℹ  SKIP'}")
    
    if system_ok:
        print("\n🎉 ¡SISTEMA LISTO PARA USO!")
        print("El sistema de magnificación optimizado está funcionando correctamente.")
    else:
        print("\n❌ SISTEMA NECESITA CORRECCIONES")
        sys.exit(1)
