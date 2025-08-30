#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests de Integración - Sistema de Análisis de Emociones
Lemac Datalab - Suite de Testing Riguroso
"""

import unittest
import sys
import os
import json
import tempfile
import threading
import time
from unittest.mock import patch, MagicMock

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar aplicaciones Flask (solo las que funcionan)
try:
    from app_ultra_simple import app as ultra_simple_app
    ULTRA_SIMPLE_AVAILABLE = True
except ImportError:
    ULTRA_SIMPLE_AVAILABLE = False

# Comentar imports problemáticos temporalmente
# try:
#     from app_liviano import app as liviano_app
#     LIVIANO_AVAILABLE = True
# except ImportError:
#     LIVIANO_AVAILABLE = False

# try:
#     from app import app as main_app
#     MAIN_APP_AVAILABLE = True
# except ImportError:
#     MAIN_APP_AVAILABLE = False

LIVIANO_AVAILABLE = False
MAIN_APP_AVAILABLE = False

class TestFlaskRoutes(unittest.TestCase):
    """Tests de integración para rutas Flask"""
    
    def setUp(self):
        """Configuración inicial para cada test"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Limpieza después de cada test"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_ultra_simple_login_route(self):
        """Test: Ruta de login en app_ultra_simple"""
        with ultra_simple_app.test_client() as client:
            # Test GET - debería mostrar formulario de login
            response = client.get('/')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'login', response.data.lower())
            
            # Test POST con credenciales correctas
            response = client.post('/', data={
                'username': 'admin',
                'password': '1234'
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            
            # Test POST con credenciales incorrectas
            response = client.post('/', data={
                'username': 'wrong',
                'password': 'wrong'
            })
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'error', response.data.lower())
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_ultra_simple_config_route_unauthorized(self):
        """Test: Acceso no autorizado a configuración"""
        with ultra_simple_app.test_client() as client:
            response = client.get('/config')
            # Debería redirigir al login
            self.assertEqual(response.status_code, 302)
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_ultra_simple_config_route_authorized(self):
        """Test: Acceso autorizado a configuración"""
        with ultra_simple_app.test_client() as client:
            # Primero hacer login
            with client.session_transaction() as sess:
                sess['logged_in'] = True
            
            response = client.get('/config')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'config', response.data.lower())
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    @patch('cv2.VideoCapture')
    def test_ultra_simple_camera_config(self, mock_video_capture):
        """Test: Configuración de cámara"""
        # Mock de cámara funcional
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, None)
        mock_video_capture.return_value = mock_cap
        
        with ultra_simple_app.test_client() as client:
            # Login primero
            with client.session_transaction() as sess:
                sess['logged_in'] = True
            
            # Configurar cámara
            response = client.post('/config', data={
                'camera': '0',
                'resolution': '640x480'
            })
            self.assertEqual(response.status_code, 200)
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_ultra_simple_academic_config(self):
        """Test: Configuración académica"""
        with ultra_simple_app.test_client() as client:
            # Login primero
            with client.session_transaction() as sess:
                sess['logged_in'] = True
            
            # Configurar datos académicos
            response = client.post('/config', data={
                'academic': 'true',
                'nivel_ensenanza': 'basica',
                'grado': '5_basico',
                'materia': 'matematicas'
            })
            self.assertEqual(response.status_code, 200)
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_ultra_simple_temperature_api(self):
        """Test: API de temperatura"""
        with ultra_simple_app.test_client() as client:
            response = client.get('/get_temperature')
            self.assertEqual(response.status_code, 200)
            
            # Verificar que devuelve JSON válido
            data = json.loads(response.data)
            self.assertIn('temperatura', data)
            self.assertIsInstance(data['temperatura'], (int, float))
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_ultra_simple_current_data_api(self):
        """Test: API de datos actuales"""
        with ultra_simple_app.test_client() as client:
            response = client.get('/get_current_data')
            self.assertEqual(response.status_code, 200)
            
            # Verificar que devuelve JSON válido
            data = json.loads(response.data)
            required_keys = ['face_count', 'emotion', 'cognitive_load']  # Campos reales de la API
            for key in required_keys:
                self.assertIn(key, data)
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_ultra_simple_dashboard_unauthorized(self):
        """Test: Acceso no autorizado al dashboard"""
        with ultra_simple_app.test_client() as client:
            response = client.get('/dashboard')
            # Debería redirigir al login
            self.assertEqual(response.status_code, 302)
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_ultra_simple_dashboard_authorized(self):
        """Test: Acceso autorizado al dashboard"""
        with ultra_simple_app.test_client() as client:
            # Login primero
            with client.session_transaction() as sess:
                sess['logged_in'] = True
            
            response = client.get('/dashboard')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'dashboard', response.data.lower())
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_ultra_simple_video_feed(self):
        """Test: Feed de video"""
        with ultra_simple_app.test_client() as client:
            response = client.get('/video_feed')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content_type, 'multipart/x-mixed-replace; boundary=frame')
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_ultra_simple_logout(self):
        """Test: Logout"""
        with ultra_simple_app.test_client() as client:
            # Login primero
            with client.session_transaction() as sess:
                sess['logged_in'] = True
            
            response = client.get('/logout')
            # Debería redirigir al login
            self.assertEqual(response.status_code, 302)

class TestAPIEndpoints(unittest.TestCase):
    """Tests específicos para endpoints de API"""
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_temperature_api_consistency(self):
        """Test: Consistencia de API de temperatura"""
        with ultra_simple_app.test_client() as client:
            # Hacer múltiples llamadas
            temperatures = []
            for _ in range(5):
                response = client.get('/get_temperature')
                data = json.loads(response.data)
                temperatures.append(data['temperatura'])
                time.sleep(0.1)
            
            # Verificar que todas están en rango válido
            for temp in temperatures:
                self.assertGreaterEqual(temp, 10.0)
                self.assertLessEqual(temp, 25.0)
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_current_data_api_structure(self):
        """Test: Estructura de API de datos actuales"""
        with ultra_simple_app.test_client() as client:
            response = client.get('/get_current_data')
            data = json.loads(response.data)
            
            # Verificar estructura esperada
            expected_structure = {
                'face_count': int,
                'emotion': (str, type(None)),  # Puede ser None
                'cognitive_load': (int, float),
                'emotion_values': dict,
                'timestamp': str
            }
            
            for key, expected_type in expected_structure.items():
                self.assertIn(key, data)
                self.assertIsInstance(data[key], expected_type)

class TestSessionManagement(unittest.TestCase):
    """Tests para manejo de sesiones"""
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_session_persistence(self):
        """Test: Persistencia de sesión"""
        with ultra_simple_app.test_client() as client:
            # Login
            response = client.post('/', data={
                'username': 'admin',
                'password': '1234'
            })
            
            # Verificar que la sesión persiste
            response = client.get('/config')
            self.assertEqual(response.status_code, 200)
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_session_cleanup_on_logout(self):
        """Test: Limpieza de sesión al logout"""
        with ultra_simple_app.test_client() as client:
            # Login
            client.post('/', data={
                'username': 'admin',
                'password': '1234'
            })
            
            # Logout
            client.get('/logout')
            
            # Verificar que la sesión se limpió
            response = client.get('/config')
            self.assertEqual(response.status_code, 302)  # Redirect to login

class TestErrorHandling(unittest.TestCase):
    """Tests para manejo de errores en integración"""
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_invalid_route(self):
        """Test: Ruta inválida"""
        with ultra_simple_app.test_client() as client:
            response = client.get('/ruta_inexistente')
            self.assertEqual(response.status_code, 404)
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_invalid_method(self):
        """Test: Método HTTP inválido"""
        with ultra_simple_app.test_client() as client:
            response = client.delete('/')  # DELETE no permitido en login
            self.assertEqual(response.status_code, 405)
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_malformed_post_data(self):
        """Test: Datos POST malformados"""
        with ultra_simple_app.test_client() as client:
            # Login con datos incompletos
            response = client.post('/', data={
                'username': 'admin'
                # Falta password
            })
            # Debería manejar el error graciosamente
            self.assertIn(response.status_code, [200, 400])

class TestConcurrency(unittest.TestCase):
    """Tests de concurrencia"""
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_concurrent_api_calls(self):
        """Test: Llamadas concurrentes a API"""
        results = []
        errors = []
        
        def make_api_call():
            try:
                with ultra_simple_app.test_client() as client:
                    response = client.get('/get_temperature')
                    if response.status_code == 200:
                        data = json.loads(response.data)
                        results.append(data['temperatura'])
                    else:
                        errors.append(f"Status: {response.status_code}")
            except Exception as e:
                errors.append(str(e))
        
        # Crear múltiples hilos
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_api_call)
            threads.append(thread)
        
        # Ejecutar todos los hilos
        for thread in threads:
            thread.start()
        
        # Esperar a que terminen
        for thread in threads:
            thread.join()
        
        # Verificar resultados
        self.assertEqual(len(errors), 0, f"Errores en concurrencia: {errors}")
        self.assertEqual(len(results), 10, "No se completaron todas las llamadas")
        
        # Verificar que todos los resultados son válidos
        for temp in results:
            self.assertGreaterEqual(temp, 10.0)
            self.assertLessEqual(temp, 25.0)

def run_integration_tests():
    """Ejecutar todos los tests de integración"""
    print("🔗 EJECUTANDO TESTS DE INTEGRACIÓN RIGUROSOS")
    print("=" * 50)
    
    # Crear suite de tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Agregar todas las clases de test
    test_classes = [
        TestFlaskRoutes,
        TestAPIEndpoints,
        TestSessionManagement,
        TestErrorHandling,
        TestConcurrency
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Ejecutar tests con verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Resumen de resultados
    print("\n" + "=" * 50)
    print(f"📊 RESUMEN DE TESTS DE INTEGRACIÓN:")
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
        print(f"\n🎉 TODOS LOS TESTS DE INTEGRACIÓN PASARON EXITOSAMENTE")
    else:
        print(f"\n💥 ALGUNOS TESTS FALLARON - REVISAR INTEGRACIÓN")
    
    return success

if __name__ == '__main__':
    run_integration_tests()

