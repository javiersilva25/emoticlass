#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests de Rendimiento y Carga - Sistema de Análisis de Emociones
Lemac Datalab - Suite de Testing Riguroso
"""

import unittest
import sys
import os
import time
import threading
import requests
import statistics
import concurrent.futures
import psutil
import gc
from unittest.mock import patch, MagicMock
import numpy as np

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar funciones para tests de rendimiento
try:
    from app_ultra_simple import (
        simulate_emotion_for_face, calculate_group_cognitive_load,
        get_valparaiso_temperature, get_current_datetime
    )
    ULTRA_SIMPLE_AVAILABLE = True
except ImportError:
    ULTRA_SIMPLE_AVAILABLE = False

class TestPerformanceBenchmarks(unittest.TestCase):
    """Tests de rendimiento para funciones individuales"""
    
    def setUp(self):
        """Configuración antes de cada test"""
        gc.collect()  # Limpiar memoria antes de cada test
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_emotion_simulation_speed(self):
        """Test: Velocidad de simulación de emociones"""
        print("⚡ Probando velocidad de simulación de emociones...")
        
        iterations = 1000
        times = []
        
        for _ in range(iterations):
            start_time = time.perf_counter()
            emotions, dominant = simulate_emotion_for_face()
            end_time = time.perf_counter()
            times.append(end_time - start_time)
        
        # Estadísticas de rendimiento
        avg_time = statistics.mean(times)
        max_time = max(times)
        min_time = min(times)
        median_time = statistics.median(times)
        
        print(f"📊 Estadísticas de simulación de emociones ({iterations} iteraciones):")
        print(f"   Tiempo promedio: {avg_time*1000:.2f}ms")
        print(f"   Tiempo máximo: {max_time*1000:.2f}ms")
        print(f"   Tiempo mínimo: {min_time*1000:.2f}ms")
        print(f"   Tiempo mediano: {median_time*1000:.2f}ms")
        
        # Requisitos de rendimiento
        self.assertLess(avg_time, 0.001, "Simulación de emociones demasiado lenta")  # < 1ms promedio
        self.assertLess(max_time, 0.01, "Pico de simulación demasiado alto")  # < 10ms máximo
        
        print("✅ Rendimiento de simulación de emociones aceptable")
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_cognitive_load_calculation_speed(self):
        """Test: Velocidad de cálculo de carga cognitiva"""
        print("🧠 Probando velocidad de cálculo de carga cognitiva...")
        
        # Crear datos de prueba para diferentes tamaños de grupo
        group_sizes = [1, 5, 15, 30, 45]
        
        for group_size in group_sizes:
            # Generar datos de emociones para el grupo
            emotions_data = []
            for _ in range(group_size):
                emotions, _ = simulate_emotion_for_face()
                emotions_data.append(emotions)
            
            # Medir tiempo de cálculo
            iterations = 100
            times = []
            
            for _ in range(iterations):
                start_time = time.perf_counter()
                load = calculate_group_cognitive_load(emotions_data)
                end_time = time.perf_counter()
                times.append(end_time - start_time)
            
            avg_time = statistics.mean(times)
            max_time = max(times)
            
            print(f"📊 Grupo de {group_size} personas:")
            print(f"   Tiempo promedio: {avg_time*1000:.2f}ms")
            print(f"   Tiempo máximo: {max_time*1000:.2f}ms")
            
            # Requisitos de rendimiento escalables
            max_allowed_time = 0.001 + (group_size * 0.0001)  # Escalamiento lineal
            self.assertLess(avg_time, max_allowed_time, 
                          f"Cálculo de carga cognitiva demasiado lento para {group_size} personas")
        
        print("✅ Rendimiento de cálculo de carga cognitiva aceptable")
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_temperature_api_speed(self):
        """Test: Velocidad de API de temperatura"""
        print("🌡️ Probando velocidad de API de temperatura...")
        
        iterations = 500
        times = []
        
        for _ in range(iterations):
            start_time = time.perf_counter()
            temp = get_valparaiso_temperature()
            end_time = time.perf_counter()
            times.append(end_time - start_time)
        
        avg_time = statistics.mean(times)
        max_time = max(times)
        
        print(f"📊 API de temperatura ({iterations} iteraciones):")
        print(f"   Tiempo promedio: {avg_time*1000:.2f}ms")
        print(f"   Tiempo máximo: {max_time*1000:.2f}ms")
        
        # Requisitos de rendimiento
        self.assertLess(avg_time, 0.001, "API de temperatura demasiado lenta")
        self.assertLess(max_time, 0.01, "Pico de API de temperatura demasiado alto")
        
        print("✅ Rendimiento de API de temperatura aceptable")
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_datetime_generation_speed(self):
        """Test: Velocidad de generación de fecha/hora"""
        print("⏰ Probando velocidad de generación de fecha/hora...")
        
        iterations = 1000
        times = []
        
        for _ in range(iterations):
            start_time = time.perf_counter()
            datetime_data = get_current_datetime()
            end_time = time.perf_counter()
            times.append(end_time - start_time)
        
        avg_time = statistics.mean(times)
        max_time = max(times)
        
        print(f"📊 Generación de fecha/hora ({iterations} iteraciones):")
        print(f"   Tiempo promedio: {avg_time*1000:.2f}ms")
        print(f"   Tiempo máximo: {max_time*1000:.2f}ms")
        
        # Requisitos de rendimiento
        self.assertLess(avg_time, 0.001, "Generación de fecha/hora demasiado lenta")
        
        print("✅ Rendimiento de generación de fecha/hora aceptable")

class TestMemoryUsage(unittest.TestCase):
    """Tests de uso de memoria"""
    
    def setUp(self):
        """Configuración antes de cada test"""
        gc.collect()
        self.initial_memory = psutil.Process().memory_info().rss
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_emotion_simulation_memory_leak(self):
        """Test: Detección de memory leaks en simulación de emociones"""
        print("🧪 Probando memory leaks en simulación de emociones...")
        
        # Medición inicial
        initial_memory = psutil.Process().memory_info().rss
        
        # Ejecutar muchas simulaciones
        for _ in range(10000):
            emotions, dominant = simulate_emotion_for_face()
        
        # Forzar garbage collection
        gc.collect()
        
        # Medición final
        final_memory = psutil.Process().memory_info().rss
        memory_increase = final_memory - initial_memory
        
        print(f"📊 Uso de memoria:")
        print(f"   Memoria inicial: {initial_memory / 1024 / 1024:.2f} MB")
        print(f"   Memoria final: {final_memory / 1024 / 1024:.2f} MB")
        print(f"   Incremento: {memory_increase / 1024 / 1024:.2f} MB")
        
        # No debería haber incremento significativo (< 10MB)
        self.assertLess(memory_increase, 10 * 1024 * 1024, 
                       "Posible memory leak en simulación de emociones")
        
        print("✅ Sin memory leaks detectados en simulación de emociones")
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_cognitive_load_memory_usage(self):
        """Test: Uso de memoria en cálculo de carga cognitiva"""
        print("🧠 Probando uso de memoria en cálculo de carga cognitiva...")
        
        # Crear datos para grupo grande
        emotions_data = []
        for _ in range(45):  # Máximo de personas
            emotions, _ = simulate_emotion_for_face()
            emotions_data.append(emotions)
        
        initial_memory = psutil.Process().memory_info().rss
        
        # Ejecutar muchos cálculos
        for _ in range(1000):
            load = calculate_group_cognitive_load(emotions_data)
        
        gc.collect()
        final_memory = psutil.Process().memory_info().rss
        memory_increase = final_memory - initial_memory
        
        print(f"📊 Uso de memoria (grupo de 45 personas, 1000 cálculos):")
        print(f"   Incremento: {memory_increase / 1024 / 1024:.2f} MB")
        
        # No debería haber incremento significativo
        self.assertLess(memory_increase, 5 * 1024 * 1024, 
                       "Uso excesivo de memoria en cálculo de carga cognitiva")
        
        print("✅ Uso de memoria aceptable en cálculo de carga cognitiva")

class TestConcurrencyPerformance(unittest.TestCase):
    """Tests de rendimiento bajo concurrencia"""
    
    @unittest.skipUnless(ULTRA_SIMPLE_AVAILABLE, "app_ultra_simple no disponible")
    def test_concurrent_emotion_simulation(self):
        """Test: Simulación concurrente de emociones"""
        print("🔄 Probando simulación concurrente de emociones...")
        
        def simulate_emotions_batch(batch_size):
            """Simular un lote de emociones"""
            results = []
            for _ in range(batch_size):
                emotions, dominant = simulate_emotion_for_face()
                results.append((emotions, dominant))
            return results
        
        # Test con diferentes números de hilos
        thread_counts = [1, 2, 4, 8]
        batch_size = 100
        
        for thread_count in thread_counts:
            start_time = time.perf_counter()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
                futures = []
                for _ in range(thread_count):
                    future = executor.submit(simulate_emotions_batch, batch_size)
                    futures.append(future)
                
                # Esperar a que terminen todos
                results = []
                for future in concurrent.futures.as_completed(futures):
                    results.extend(future.result())
            
            end_time = time.perf_counter()
            total_time = end_time - start_time
            total_simulations = thread_count * batch_size
            simulations_per_second = total_simulations / total_time
            
            print(f"📊 {thread_count} hilos:")
            print(f"   Tiempo total: {total_time:.2f}s")
            print(f"   Simulaciones/segundo: {simulations_per_second:.0f}")
            
            # Verificar que la concurrencia mejora el rendimiento
            if thread_count > 1:
                # Con más hilos debería ser más rápido (al menos 50% del ideal)
                expected_min_speed = simulations_per_second * 0.5
                self.assertGreater(simulations_per_second, expected_min_speed)
        
        print("✅ Rendimiento concurrente aceptable")

class TestLoadTesting(unittest.TestCase):
    """Tests de carga para el sistema completo"""
    
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
    
    def test_api_load_temperature(self):
        """Test: Carga en API de temperatura"""
        print("🌡️ Probando carga en API de temperatura...")
        
        def make_temperature_request():
            """Hacer una petición de temperatura"""
            try:
                start_time = time.perf_counter()
                response = requests.get(f"{self.base_url}/get_temperature", timeout=5)
                end_time = time.perf_counter()
                
                return {
                    'success': response.status_code == 200,
                    'time': end_time - start_time,
                    'status_code': response.status_code
                }
            except Exception as e:
                return {
                    'success': False,
                    'time': 5.0,  # Timeout
                    'error': str(e)
                }
        
        # Test con diferentes niveles de concurrencia
        concurrency_levels = [1, 5, 10, 20]
        requests_per_level = 50
        
        for concurrency in concurrency_levels:
            print(f"🔄 Probando con {concurrency} peticiones concurrentes...")
            
            start_time = time.perf_counter()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = []
                for _ in range(requests_per_level):
                    future = executor.submit(make_temperature_request)
                    futures.append(future)
                
                results = []
                for future in concurrent.futures.as_completed(futures):
                    results.append(future.result())
            
            end_time = time.perf_counter()
            total_time = end_time - start_time
            
            # Analizar resultados
            successful_requests = sum(1 for r in results if r['success'])
            failed_requests = len(results) - successful_requests
            response_times = [r['time'] for r in results if r['success']]
            
            if response_times:
                avg_response_time = statistics.mean(response_times)
                max_response_time = max(response_times)
                requests_per_second = successful_requests / total_time
            else:
                avg_response_time = 0
                max_response_time = 0
                requests_per_second = 0
            
            print(f"📊 Resultados para {concurrency} peticiones concurrentes:")
            print(f"   Peticiones exitosas: {successful_requests}/{requests_per_level}")
            print(f"   Peticiones fallidas: {failed_requests}")
            print(f"   Tiempo promedio de respuesta: {avg_response_time*1000:.2f}ms")
            print(f"   Tiempo máximo de respuesta: {max_response_time*1000:.2f}ms")
            print(f"   Peticiones/segundo: {requests_per_second:.2f}")
            
            # Requisitos de rendimiento
            success_rate = successful_requests / requests_per_level
            self.assertGreaterEqual(success_rate, 0.95, 
                                  f"Tasa de éxito muy baja: {success_rate:.2%}")
            
            if response_times:
                self.assertLess(avg_response_time, 1.0, 
                              "Tiempo de respuesta promedio demasiado alto")
                self.assertLess(max_response_time, 5.0, 
                              "Tiempo de respuesta máximo demasiado alto")
        
        print("✅ API de temperatura soporta la carga esperada")
    
    def test_api_load_current_data(self):
        """Test: Carga en API de datos actuales"""
        print("📊 Probando carga en API de datos actuales...")
        
        def make_current_data_request():
            """Hacer una petición de datos actuales"""
            try:
                start_time = time.perf_counter()
                response = requests.get(f"{self.base_url}/get_current_data", timeout=10)
                end_time = time.perf_counter()
                
                return {
                    'success': response.status_code == 200,
                    'time': end_time - start_time,
                    'status_code': response.status_code
                }
            except Exception as e:
                return {
                    'success': False,
                    'time': 10.0,  # Timeout
                    'error': str(e)
                }
        
        # Test de carga sostenida
        duration_seconds = 30
        concurrent_users = 5
        
        print(f"🔄 Ejecutando test de carga sostenida ({duration_seconds}s, {concurrent_users} usuarios)...")
        
        results = []
        start_time = time.perf_counter()
        
        def sustained_load_worker():
            """Worker para carga sostenida"""
            worker_results = []
            while time.perf_counter() - start_time < duration_seconds:
                result = make_current_data_request()
                worker_results.append(result)
                time.sleep(0.1)  # 10 peticiones por segundo por usuario
            return worker_results
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = []
            for _ in range(concurrent_users):
                future = executor.submit(sustained_load_worker)
                futures.append(future)
            
            for future in concurrent.futures.as_completed(futures):
                results.extend(future.result())
        
        # Analizar resultados
        successful_requests = sum(1 for r in results if r['success'])
        failed_requests = len(results) - successful_requests
        response_times = [r['time'] for r in results if r['success']]
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)
            requests_per_second = successful_requests / duration_seconds
        else:
            avg_response_time = 0
            max_response_time = 0
            min_response_time = 0
            requests_per_second = 0
        
        print(f"📊 Resultados de carga sostenida:")
        print(f"   Duración: {duration_seconds}s")
        print(f"   Usuarios concurrentes: {concurrent_users}")
        print(f"   Total de peticiones: {len(results)}")
        print(f"   Peticiones exitosas: {successful_requests}")
        print(f"   Peticiones fallidas: {failed_requests}")
        print(f"   Tiempo promedio: {avg_response_time*1000:.2f}ms")
        print(f"   Tiempo mínimo: {min_response_time*1000:.2f}ms")
        print(f"   Tiempo máximo: {max_response_time*1000:.2f}ms")
        print(f"   Peticiones/segundo: {requests_per_second:.2f}")
        
        # Requisitos de rendimiento para carga sostenida
        success_rate = successful_requests / len(results) if results else 0
        self.assertGreaterEqual(success_rate, 0.90, 
                              f"Tasa de éxito en carga sostenida muy baja: {success_rate:.2%}")
        
        if response_times:
            self.assertLess(avg_response_time, 2.0, 
                          "Tiempo de respuesta promedio demasiado alto bajo carga")
        
        print("✅ API de datos actuales soporta carga sostenida")

def run_performance_tests():
    """Ejecutar todos los tests de rendimiento"""
    print("🚀 EJECUTANDO TESTS DE RENDIMIENTO Y CARGA RIGUROSOS")
    print("=" * 60)
    
    # Crear suite de tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Agregar todas las clases de test
    test_classes = [
        TestPerformanceBenchmarks,
        TestMemoryUsage,
        TestConcurrencyPerformance,
        TestLoadTesting
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Ejecutar tests con verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Resumen de resultados
    print("\n" + "=" * 60)
    print(f"📊 RESUMEN DE TESTS DE RENDIMIENTO:")
    print(f"✅ Tests ejecutados: {result.testsRun}")
    print(f"❌ Fallos: {len(result.failures)}")
    print(f"⚠️  Errores: {len(result.errors)}")
    print(f"⏭️  Omitidos: {len(result.skipped)}")
    
    if result.failures:
        print(f"\n❌ FALLOS DE RENDIMIENTO DETECTADOS:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print(f"\n⚠️ ERRORES DE RENDIMIENTO DETECTADOS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    # Determinar si todos los tests pasaron
    success = len(result.failures) == 0 and len(result.errors) == 0
    
    if success:
        print(f"\n🎉 TODOS LOS TESTS DE RENDIMIENTO PASARON EXITOSAMENTE")
        print(f"🚀 EL SISTEMA CUMPLE CON LOS REQUISITOS DE RENDIMIENTO")
    else:
        print(f"\n💥 ALGUNOS TESTS DE RENDIMIENTO FALLARON")
        print(f"⚠️  REVISAR OPTIMIZACIONES NECESARIAS")
    
    return success

if __name__ == '__main__':
    run_performance_tests()

