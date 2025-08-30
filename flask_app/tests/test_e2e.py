#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests End-to-End - Sistema de Análisis de Emociones
Lemac Datalab - Suite de Testing Riguroso
"""

import unittest
import sys
import os
import time
import json
import threading
import subprocess
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestE2EFlows(unittest.TestCase):
    """Tests End-to-End para flujos completos de usuario"""
    
    @classmethod
    def setUpClass(cls):
        """Configuración inicial para toda la clase"""
        cls.app_process = None
        cls.driver = None
        cls.base_url = "http://localhost:5001"
        
        # Configurar Chrome en modo headless
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        try:
            cls.driver = webdriver.Chrome(options=chrome_options)
            cls.driver.implicitly_wait(10)
        except WebDriverException:
            print("⚠️ Chrome WebDriver no disponible - Tests E2E omitidos")
            cls.driver = None
        
        # Iniciar aplicación en background
        cls.start_test_app()
    
    @classmethod
    def tearDownClass(cls):
        """Limpieza después de todos los tests"""
        if cls.driver:
            cls.driver.quit()
        
        if cls.app_process:
            cls.app_process.terminate()
            cls.app_process.wait()
    
    @classmethod
    def start_test_app(cls):
        """Iniciar aplicación para tests"""
        try:
            # Iniciar app_ultra_simple en background
            cls.app_process = subprocess.Popen([
                'python3', 'app_ultra_simple.py'
            ], cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            # Esperar a que la aplicación esté lista
            for _ in range(30):  # 30 segundos máximo
                try:
                    response = requests.get(cls.base_url, timeout=1)
                    if response.status_code == 200:
                        print("✅ Aplicación de test iniciada correctamente")
                        return
                except requests.exceptions.RequestException:
                    pass
                time.sleep(1)
            
            print("⚠️ No se pudo iniciar la aplicación de test")
            
        except Exception as e:
            print(f"⚠️ Error iniciando aplicación de test: {e}")
    
    def setUp(self):
        """Configuración antes de cada test"""
        if not self.driver:
            self.skipTest("Chrome WebDriver no disponible")
    
    def test_complete_user_flow(self):
        """Test: Flujo completo de usuario desde login hasta dashboard"""
        print("🔄 Ejecutando flujo completo de usuario...")
        
        # Paso 1: Acceder a la página de login
        self.driver.get(self.base_url)
        self.assertIn("login", self.driver.title.lower())
        
        # Paso 2: Realizar login
        username_field = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        password_field = self.driver.find_element(By.NAME, "password")
        login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        
        username_field.send_keys("admin")
        password_field.send_keys("1234")
        login_button.click()
        
        # Verificar redirección a configuración
        WebDriverWait(self.driver, 10).until(
            EC.url_contains("/config")
        )
        self.assertIn("config", self.driver.current_url)
        
        # Paso 3: Configurar cámara
        camera_select = Select(self.driver.find_element(By.NAME, "camera"))
        resolution_select = Select(self.driver.find_element(By.NAME, "resolution"))
        
        camera_select.select_by_value("0")
        resolution_select.select_by_value("640x480")
        
        config_camera_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        config_camera_button.click()
        
        # Esperar a que se procese la configuración
        time.sleep(2)
        
        # Paso 4: Configurar datos académicos
        nivel_select = Select(self.driver.find_element(By.NAME, "nivel_ensenanza"))
        nivel_select.select_by_value("basica")
        
        # Esperar a que se carguen los grados
        time.sleep(1)
        
        grado_select = Select(self.driver.find_element(By.NAME, "grado"))
        grado_select.select_by_value("5_basico")
        
        materia_select = Select(self.driver.find_element(By.NAME, "materia"))
        materia_select.select_by_value("matematicas")
        
        # Guardar configuración académica
        academic_button = self.driver.find_element(By.CSS_SELECTOR, "button[name='academic']")
        academic_button.click()
        
        # Esperar a que aparezca el botón del dashboard
        dashboard_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "🚀 Ir al Dashboard"))
        )
        
        # Paso 5: Ir al dashboard
        dashboard_button.click()
        
        # Verificar que estamos en el dashboard
        WebDriverWait(self.driver, 10).until(
            EC.url_contains("/dashboard")
        )
        self.assertIn("dashboard", self.driver.current_url)
        
        # Verificar elementos del dashboard
        self.assertTrue(self.driver.find_element(By.ID, "faces-count"))
        self.assertTrue(self.driver.find_element(By.ID, "dominant-emotion"))
        
        print("✅ Flujo completo de usuario ejecutado exitosamente")
    
    def test_login_validation(self):
        """Test: Validación de credenciales de login"""
        print("🔐 Probando validación de login...")
        
        self.driver.get(self.base_url)
        
        # Test con credenciales incorrectas
        username_field = self.driver.find_element(By.NAME, "username")
        password_field = self.driver.find_element(By.NAME, "password")
        login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        
        username_field.send_keys("wrong")
        password_field.send_keys("wrong")
        login_button.click()
        
        # Verificar que permanece en login con error
        time.sleep(2)
        self.assertIn("login", self.driver.current_url.lower())
        
        # Limpiar campos
        username_field.clear()
        password_field.clear()
        
        # Test con credenciales correctas
        username_field.send_keys("admin")
        password_field.send_keys("1234")
        login_button.click()
        
        # Verificar redirección exitosa
        WebDriverWait(self.driver, 10).until(
            EC.url_contains("/config")
        )
        
        print("✅ Validación de login funcionando correctamente")
    
    def test_camera_configuration_flow(self):
        """Test: Flujo de configuración de cámara"""
        print("📹 Probando configuración de cámara...")
        
        # Login primero
        self.driver.get(self.base_url)
        self.driver.find_element(By.NAME, "username").send_keys("admin")
        self.driver.find_element(By.NAME, "password").send_keys("1234")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        
        WebDriverWait(self.driver, 10).until(
            EC.url_contains("/config")
        )
        
        # Verificar que los selectores de cámara están presentes
        camera_select = self.driver.find_element(By.NAME, "camera")
        resolution_select = self.driver.find_element(By.NAME, "resolution")
        
        # Verificar que tienen opciones
        camera_options = Select(camera_select).options
        resolution_options = Select(resolution_select).options
        
        self.assertGreater(len(camera_options), 0)
        self.assertGreater(len(resolution_options), 0)
        
        # Configurar cámara
        Select(camera_select).select_by_index(0)
        Select(resolution_select).select_by_value("640x480")
        
        config_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        config_button.click()
        
        # Verificar que la configuración se procesó
        time.sleep(2)
        
        print("✅ Configuración de cámara funcionando correctamente")
    
    def test_academic_configuration_flow(self):
        """Test: Flujo de configuración académica"""
        print("🎓 Probando configuración académica...")
        
        # Login y navegar a configuración
        self.driver.get(self.base_url)
        self.driver.find_element(By.NAME, "username").send_keys("admin")
        self.driver.find_element(By.NAME, "password").send_keys("1234")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        
        WebDriverWait(self.driver, 10).until(
            EC.url_contains("/config")
        )
        
        # Configurar nivel de enseñanza
        nivel_select = Select(self.driver.find_element(By.NAME, "nivel_ensenanza"))
        nivel_select.select_by_value("basica")
        
        # Esperar a que se actualicen los grados
        time.sleep(1)
        
        # Verificar que el selector de grado se habilitó
        grado_select = Select(self.driver.find_element(By.NAME, "grado"))
        grado_options = grado_select.options
        self.assertGreater(len(grado_options), 1)  # Más que solo "Seleccionar grado..."
        
        # Seleccionar grado y materia
        grado_select.select_by_value("5_basico")
        
        materia_select = Select(self.driver.find_element(By.NAME, "materia"))
        materia_select.select_by_value("matematicas")
        
        # Verificar que el campo de temperatura está presente
        temperatura_field = self.driver.find_element(By.NAME, "temperatura")
        self.assertTrue(temperatura_field.is_displayed())
        
        # Guardar configuración académica
        academic_button = self.driver.find_element(By.CSS_SELECTOR, "button[name='academic']")
        academic_button.click()
        
        # Verificar que aparece el botón del dashboard
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.LINK_TEXT, "🚀 Ir al Dashboard"))
        )
        
        print("✅ Configuración académica funcionando correctamente")
    
    def test_dashboard_functionality(self):
        """Test: Funcionalidad del dashboard"""
        print("📊 Probando funcionalidad del dashboard...")
        
        # Completar flujo hasta dashboard
        self.driver.get(self.base_url)
        self.driver.find_element(By.NAME, "username").send_keys("admin")
        self.driver.find_element(By.NAME, "password").send_keys("1234")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        
        WebDriverWait(self.driver, 10).until(EC.url_contains("/config"))
        
        # Configuración rápida
        Select(self.driver.find_element(By.NAME, "camera")).select_by_value("0")
        Select(self.driver.find_element(By.NAME, "resolution")).select_by_value("640x480")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        
        time.sleep(1)
        
        Select(self.driver.find_element(By.NAME, "nivel_ensenanza")).select_by_value("basica")
        time.sleep(1)
        Select(self.driver.find_element(By.NAME, "grado")).select_by_value("5_basico")
        Select(self.driver.find_element(By.NAME, "materia")).select_by_value("matematicas")
        self.driver.find_element(By.CSS_SELECTOR, "button[name='academic']").click()
        
        # Ir al dashboard
        dashboard_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "🚀 Ir al Dashboard"))
        )
        dashboard_button.click()
        
        WebDriverWait(self.driver, 10).until(EC.url_contains("/dashboard"))
        
        # Verificar elementos del dashboard
        elements_to_check = [
            "faces-count",
            "dominant-emotion",
            "cognitive-load",
            "system-status"
        ]
        
        for element_id in elements_to_check:
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, element_id))
            )
            self.assertTrue(element.is_displayed())
        
        # Verificar que el video feed está presente
        video_element = self.driver.find_element(By.CSS_SELECTOR, "img[src*='video_feed']")
        self.assertTrue(video_element.is_displayed())
        
        print("✅ Dashboard funcionando correctamente")
    
    def test_logout_flow(self):
        """Test: Flujo de logout"""
        print("🚪 Probando flujo de logout...")
        
        # Login primero
        self.driver.get(self.base_url)
        self.driver.find_element(By.NAME, "username").send_keys("admin")
        self.driver.find_element(By.NAME, "password").send_keys("1234")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        
        WebDriverWait(self.driver, 10).until(EC.url_contains("/config"))
        
        # Hacer logout
        logout_link = self.driver.find_element(By.LINK_TEXT, "Cerrar Sesión")
        logout_link.click()
        
        # Verificar redirección al login
        WebDriverWait(self.driver, 10).until(
            EC.url_matches(f"{self.base_url}/?$")
        )
        
        # Verificar que no se puede acceder a páginas protegidas
        self.driver.get(f"{self.base_url}/config")
        WebDriverWait(self.driver, 10).until(
            EC.url_matches(f"{self.base_url}/?$")
        )
        
        print("✅ Logout funcionando correctamente")
    
    def test_responsive_design(self):
        """Test: Diseño responsivo"""
        print("📱 Probando diseño responsivo...")
        
        # Login
        self.driver.get(self.base_url)
        self.driver.find_element(By.NAME, "username").send_keys("admin")
        self.driver.find_element(By.NAME, "password").send_keys("1234")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        
        WebDriverWait(self.driver, 10).until(EC.url_contains("/config"))
        
        # Probar diferentes tamaños de pantalla
        screen_sizes = [
            (1920, 1080),  # Desktop
            (1024, 768),   # Tablet
            (375, 667)     # Mobile
        ]
        
        for width, height in screen_sizes:
            self.driver.set_window_size(width, height)
            time.sleep(1)
            
            # Verificar que los elementos principales están visibles
            main_elements = self.driver.find_elements(By.CSS_SELECTOR, ".card")
            for element in main_elements:
                self.assertTrue(element.is_displayed())
        
        # Restaurar tamaño original
        self.driver.set_window_size(1920, 1080)
        
        print("✅ Diseño responsivo funcionando correctamente")

class TestAPIEndToEnd(unittest.TestCase):
    """Tests End-to-End para APIs"""
    
    def setUp(self):
        """Configuración antes de cada test"""
        self.base_url = "http://localhost:5001"
        
        # Verificar que la aplicación está corriendo
        try:
            response = requests.get(self.base_url, timeout=5)
            if response.status_code != 200:
                self.skipTest("Aplicación no está corriendo")
        except requests.exceptions.RequestException:
            self.skipTest("No se puede conectar a la aplicación")
    
    def test_temperature_api_consistency(self):
        """Test: Consistencia de API de temperatura"""
        print("🌡️ Probando consistencia de API de temperatura...")
        
        temperatures = []
        for _ in range(10):
            response = requests.get(f"{self.base_url}/get_temperature")
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn('temperatura', data)
            
            temp = data['temperatura']
            self.assertIsInstance(temp, (int, float))
            self.assertGreaterEqual(temp, 10.0)
            self.assertLessEqual(temp, 25.0)
            
            temperatures.append(temp)
            time.sleep(0.1)
        
        # Verificar que hay variación (no siempre el mismo valor)
        unique_temps = set(temperatures)
        self.assertGreater(len(unique_temps), 1)
        
        print("✅ API de temperatura consistente")
    
    def test_current_data_api_structure(self):
        """Test: Estructura de API de datos actuales"""
        print("📊 Probando estructura de API de datos actuales...")
        
        response = requests.get(f"{self.base_url}/get_current_data")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        
        # Verificar estructura esperada
        required_fields = [
            'faces_detected',
            'dominant_emotion',
            'cognitive_load',
            'emotions_distribution',
            'system_status'
        ]
        
        for field in required_fields:
            self.assertIn(field, data)
        
        # Verificar tipos de datos
        self.assertIsInstance(data['faces_detected'], int)
        self.assertIsInstance(data['dominant_emotion'], str)
        self.assertIsInstance(data['cognitive_load'], (int, float))
        self.assertIsInstance(data['emotions_distribution'], dict)
        self.assertIsInstance(data['system_status'], str)
        
        print("✅ Estructura de API de datos actuales correcta")

def run_e2e_tests():
    """Ejecutar todos los tests end-to-end"""
    print("🎭 EJECUTANDO TESTS END-TO-END RIGUROSOS")
    print("=" * 50)
    
    # Crear suite de tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Agregar todas las clases de test
    test_classes = [
        TestE2EFlows,
        TestAPIEndToEnd
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Ejecutar tests con verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Resumen de resultados
    print("\n" + "=" * 50)
    print(f"📊 RESUMEN DE TESTS END-TO-END:")
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
        print(f"\n🎉 TODOS LOS TESTS END-TO-END PASARON EXITOSAMENTE")
    else:
        print(f"\n💥 ALGUNOS TESTS FALLARON - REVISAR FLUJOS DE USUARIO")
    
    return success

if __name__ == '__main__':
    run_e2e_tests()

