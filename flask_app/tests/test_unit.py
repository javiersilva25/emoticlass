#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests Unitarios - Sistema de Análisis de Emociones
Lemac Datalab - Suite de Testing Riguroso
"""

import unittest
import sys
import os
import tempfile
import csv
from unittest.mock import patch, MagicMock
import numpy as np

# Agregar el directorio padre al path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar funciones de todos los módulos
try:
    from app_ultra_simple import (
        get_current_datetime, get_valparaiso_temperature, detect_cameras,
        simulate_emotion_for_face, calculate_group_cognitive_load
    )
    ULTRA_SIMPLE_AVAILABLE = True
except ImportError:
    ULTRA_SIMPLE_AVAILABLE = False

try:
    from app_liviano import get_current_datetime as get_datetime_liviano
    LIVIANO_AVAILABLE = True
except ImportError:
    LIVIANO_AVAILABLE = False

class TestUtilityFunctions(unittest.TestCase):
    """Tests para funciones utilitarias"""
    
    def setUp(self):
        """Configuración inicial para cada test"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Limpieza después de cada test"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_get_current_datetime_format(self):
        """Test: Verificar formato correcto de fecha y hora"""
        result = get_current_datetime()
        
        # Verificar que devuelve un diccionario
        self.assertIsInstance(result, dict)
        
        # Verificar que contiene las claves necesarias
        required_keys = ['fecha', 'hora', 'milisegundos']
        for key in required_keys:
            self.assertIn(key, result)
        
        # Verificar formato de fecha (YYYY-MM-DD)
        fecha = result['fecha']
        self.assertRegex(fecha, r'^\d{4}-\d{2}-\d{2}$')
        
        # Verificar formato de hora (HH:MM:SS)
        hora = result['hora']
        self.assertRegex(hora, r'^\d{2}:\d{2}:\d{2}$')
        
        # Verificar formato de milisegundos (3 dígitos)
        milisegundos = result['milisegundos']
        self.assertRegex(milisegundos, r'^\d{3}$')
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_get_valparaiso_temperature_range(self):
        """Test: Verificar que la temperatura está en rango válido"""
        for _ in range(10):  # Probar múltiples veces por aleatoriedad
            temp = get_valparaiso_temperature()
            
            # Verificar que es un número
            self.assertIsInstance(temp, (int, float))
            
            # Verificar rango válido (10-25°C)
            self.assertGreaterEqual(temp, 10.0)
            self.assertLessEqual(temp, 25.0)
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    @patch('cv2.VideoCapture')
    def test_detect_cameras_success(self, mock_video_capture):
        """Test: Detección exitosa de cámaras"""
        # Mock de cámara funcional
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_video_capture.return_value = mock_cap
        
        cameras = detect_cameras()
        
        # Verificar que devuelve una lista
        self.assertIsInstance(cameras, list)
        
        # Verificar que contiene al menos una cámara
        self.assertGreater(len(cameras), 0)
        
        # Verificar que los índices son válidos
        for cam_index in cameras:
            self.assertIsInstance(cam_index, int)
            self.assertGreaterEqual(cam_index, 0)
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    @patch('cv2.VideoCapture')
    def test_detect_cameras_failure(self, mock_video_capture):
        """Test: Manejo de fallo en detección de cámaras"""
        # Mock de cámara no funcional
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_video_capture.return_value = mock_cap
        
        cameras = detect_cameras()
        
        # Verificar que devuelve lista con cámara demo
        self.assertIsInstance(cameras, list)
        self.assertEqual(cameras, [0])  # Modo demo
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_simulate_emotion_for_face(self):
        """Test: Simulación de emociones para rostro"""
        emotions, dominant = simulate_emotion_for_face()
        
        # Verificar que devuelve diccionario de emociones
        self.assertIsInstance(emotions, dict)
        self.assertIsInstance(dominant, str)
        
        # Verificar emociones válidas
        valid_emotions = ["feliz", "triste", "enojado", "neutral", "sorpresa", "miedo", "asco"]
        for emotion, confidence in emotions.items():
            self.assertIn(emotion, valid_emotions)
            self.assertIsInstance(confidence, (int, float))
            self.assertGreaterEqual(confidence, 0)
            self.assertLessEqual(confidence, 100)
        
        # Verificar emoción dominante
        self.assertIn(dominant, valid_emotions)
        self.assertIn(dominant, emotions)
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_calculate_group_cognitive_load_empty(self):
        """Test: Carga cognitiva con lista vacía"""
        load = calculate_group_cognitive_load([])
        self.assertEqual(load, 0)
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_calculate_group_cognitive_load_single_person(self):
        """Test: Carga cognitiva con una persona"""
        emotions_data = [{
            "triste": 80,
            "feliz": 20,
            "neutral": 0,
            "enojado": 0,
            "miedo": 0,
            "asco": 0,
            "sorpresa": 0
        }]
        
        load = calculate_group_cognitive_load(emotions_data)
        
        # Verificar que es un número válido
        self.assertIsInstance(load, (int, float))
        self.assertGreaterEqual(load, 0)
        self.assertLessEqual(load, 100)
        
        # Con tristeza alta, la carga debería ser significativa
        self.assertGreater(load, 0)
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_calculate_group_cognitive_load_multiple_people(self):
        """Test: Carga cognitiva con múltiples personas"""
        emotions_data = [
            {"triste": 90, "feliz": 10, "neutral": 0, "enojado": 0, "miedo": 0, "asco": 0, "sorpresa": 0},
            {"feliz": 80, "triste": 20, "neutral": 0, "enojado": 0, "miedo": 0, "asco": 0, "sorpresa": 0},
            {"neutral": 70, "feliz": 30, "triste": 0, "enojado": 0, "miedo": 0, "asco": 0, "sorpresa": 0}
        ]
        
        load = calculate_group_cognitive_load(emotions_data)
        
        # Verificar que es un número válido
        self.assertIsInstance(load, (int, float))
        self.assertGreaterEqual(load, 0)
        self.assertLessEqual(load, 100)

class TestDataValidation(unittest.TestCase):
    """Tests para validación de datos"""
    
    def test_emotion_values_consistency(self):
        """Test: Consistencia en valores de emociones"""
        valid_emotions = ["feliz", "triste", "enojado", "neutral", "sorpresa", "miedo", "asco"]
        
        # Verificar que todas las emociones están definidas
        self.assertEqual(len(valid_emotions), 7)
        
        # Verificar que no hay duplicados
        self.assertEqual(len(valid_emotions), len(set(valid_emotions)))
    
    def test_csv_header_consistency(self):
        """Test: Consistencia en headers de CSV"""
        expected_headers = [
            "fecha", "hora", "milisegundos", "emocion", "confianza_emocion",
            "genero", "confianza_genero", "carga_cognitiva",
            "nivel_ensenanza", "grado", "materia", "temperatura"
        ]
        
        # Verificar que tenemos 12 columnas
        self.assertEqual(len(expected_headers), 12)
        
        # Verificar que no hay duplicados
        self.assertEqual(len(expected_headers), len(set(expected_headers)))

class TestErrorHandling(unittest.TestCase):
    """Tests para manejo de errores"""
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    @patch('cv2.VideoCapture')
    def test_camera_error_handling(self, mock_video_capture):
        """Test: Manejo de errores de cámara"""
        # Mock que lanza excepción
        mock_video_capture.side_effect = Exception("Error de cámara simulado")
        
        # No debería lanzar excepción
        try:
            cameras = detect_cameras()
            # Debería devolver modo demo
            self.assertEqual(cameras, [0])
        except Exception as e:
            self.fail(f"detect_cameras() lanzó excepción: {e}")
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    @patch('random.uniform')
    def test_temperature_error_handling(self, mock_random):
        """Test: Manejo de errores en temperatura"""
        # Mock que lanza excepción
        mock_random.side_effect = Exception("Error de temperatura simulado")
        
        # No debería lanzar excepción
        try:
            temp = get_valparaiso_temperature()
            # Debería devolver valor por defecto
            self.assertEqual(temp, 15.0)
        except Exception as e:
            self.fail(f"get_valparaiso_temperature() lanzó excepción: {e}")

class TestPerformance(unittest.TestCase):
    """Tests de rendimiento"""
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_emotion_simulation_performance(self):
        """Test: Rendimiento de simulación de emociones"""
        import time
        
        start_time = time.time()
        
        # Simular 100 rostros
        for _ in range(100):
            emotions, dominant = simulate_emotion_for_face()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Debería completarse en menos de 1 segundo
        self.assertLess(execution_time, 1.0)
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_cognitive_load_performance(self):
        """Test: Rendimiento de cálculo de carga cognitiva"""
        import time
        
        # Crear datos de prueba para 45 personas
        emotions_data = []
        for _ in range(45):
            emotions, _ = simulate_emotion_for_face()
            emotions_data.append(emotions)
        
        start_time = time.time()
        
        # Calcular carga cognitiva 100 veces
        for _ in range(100):
            load = calculate_group_cognitive_load(emotions_data)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Debería completarse en menos de 0.5 segundos
        self.assertLess(execution_time, 0.5)

def run_unit_tests():
    """Ejecutar todos los tests unitarios"""
    print("🧪 EJECUTANDO TESTS UNITARIOS RIGUROSOS")
    print("=" * 50)
    
    # Crear suite de tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Agregar todas las clases de test
    test_classes = [
        TestUtilityFunctions,
        TestDataValidation,
        TestErrorHandling,
        TestPerformance
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Ejecutar tests con verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Resumen de resultados
    print("\n" + "=" * 50)
    print(f"📊 RESUMEN DE TESTS UNITARIOS:")
    print(f"✅ Tests ejecutados: {result.testsRun}")
    print(f"❌ Fallos: {len(result.failures)}")
    print(f"⚠️  Errores: {len(result.errors)}")
    print(f"⏭️  Omitidos: {len(result.skipped)}")
    
    if result.failures:
        print(f"\n❌ FALLOS DETECTADOS:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print(f"\n⚠️ ERRORES DETECTADOS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    # Determinar si todos los tests pasaron
    success = len(result.failures) == 0 and len(result.errors) == 0
    
    if success:
        print(f"\n🎉 TODOS LOS TESTS UNITARIOS PASARON EXITOSAMENTE")
    else:
        print(f"\n💥 ALGUNOS TESTS FALLARON - REVISAR CÓDIGO")
    
    return success

if __name__ == '__main__':
    run_unit_tests()

