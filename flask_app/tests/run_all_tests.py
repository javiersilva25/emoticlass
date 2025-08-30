#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script Maestro de Testing - Sistema de Análisis de Emociones
Lemac Datalab - Suite de Testing Riguroso Completo
"""

import sys
import os
import time
import subprocess
import json
from datetime import datetime

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar módulos de testing
from test_unit import run_unit_tests
from test_integration import run_integration_tests
from test_e2e import run_e2e_tests
from test_performance import run_performance_tests

class TestRunner:
    """Ejecutor maestro de todos los tests"""
    
    def __init__(self):
        self.results = {
            'start_time': None,
            'end_time': None,
            'duration': None,
            'unit_tests': {'executed': False, 'passed': False, 'details': None},
            'integration_tests': {'executed': False, 'passed': False, 'details': None},
            'e2e_tests': {'executed': False, 'passed': False, 'details': None},
            'performance_tests': {'executed': False, 'passed': False, 'details': None},
            'overall_success': False,
            'summary': {}
        }
    
    def print_header(self):
        """Imprimir header del testing"""
        print("=" * 80)
        print("🧪 SISTEMA DE TESTING RIGUROSO - LEMAC DATALAB")
        print("📊 Sistema de Análisis de Emociones")
        print("=" * 80)
        print(f"🕐 Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
    
    def print_section_header(self, section_name, description):
        """Imprimir header de sección"""
        print(f"\n{'='*20} {section_name} {'='*20}")
        print(f"📋 {description}")
        print("-" * 60)
    
    def run_unit_tests_section(self):
        """Ejecutar tests unitarios"""
        self.print_section_header("TESTS UNITARIOS", "Validación de funciones individuales")
        
        try:
            start_time = time.time()
            success = run_unit_tests()
            end_time = time.time()
            
            self.results['unit_tests'] = {
                'executed': True,
                'passed': success,
                'duration': end_time - start_time,
                'details': "Tests unitarios completados"
            }
            
            if success:
                print("✅ TESTS UNITARIOS: EXITOSOS")
            else:
                print("❌ TESTS UNITARIOS: FALLARON")
                
        except Exception as e:
            print(f"💥 ERROR EN TESTS UNITARIOS: {e}")
            self.results['unit_tests'] = {
                'executed': True,
                'passed': False,
                'error': str(e)
            }
    
    def run_integration_tests_section(self):
        """Ejecutar tests de integración"""
        self.print_section_header("TESTS DE INTEGRACIÓN", "Validación de APIs y rutas Flask")
        
        try:
            start_time = time.time()
            success = run_integration_tests()
            end_time = time.time()
            
            self.results['integration_tests'] = {
                'executed': True,
                'passed': success,
                'duration': end_time - start_time,
                'details': "Tests de integración completados"
            }
            
            if success:
                print("✅ TESTS DE INTEGRACIÓN: EXITOSOS")
            else:
                print("❌ TESTS DE INTEGRACIÓN: FALLARON")
                
        except Exception as e:
            print(f"💥 ERROR EN TESTS DE INTEGRACIÓN: {e}")
            self.results['integration_tests'] = {
                'executed': True,
                'passed': False,
                'error': str(e)
            }
    
    def run_e2e_tests_section(self):
        """Ejecutar tests end-to-end"""
        self.print_section_header("TESTS END-TO-END", "Validación de flujos completos de usuario")
        
        try:
            start_time = time.time()
            success = run_e2e_tests()
            end_time = time.time()
            
            self.results['e2e_tests'] = {
                'executed': True,
                'passed': success,
                'duration': end_time - start_time,
                'details': "Tests end-to-end completados"
            }
            
            if success:
                print("✅ TESTS END-TO-END: EXITOSOS")
            else:
                print("❌ TESTS END-TO-END: FALLARON")
                
        except Exception as e:
            print(f"💥 ERROR EN TESTS END-TO-END: {e}")
            self.results['e2e_tests'] = {
                'executed': True,
                'passed': False,
                'error': str(e)
            }
    
    def run_performance_tests_section(self):
        """Ejecutar tests de rendimiento"""
        self.print_section_header("TESTS DE RENDIMIENTO", "Validación de performance y carga")
        
        try:
            start_time = time.time()
            success = run_performance_tests()
            end_time = time.time()
            
            self.results['performance_tests'] = {
                'executed': True,
                'passed': success,
                'duration': end_time - start_time,
                'details': "Tests de rendimiento completados"
            }
            
            if success:
                print("✅ TESTS DE RENDIMIENTO: EXITOSOS")
            else:
                print("❌ TESTS DE RENDIMIENTO: FALLARON")
                
        except Exception as e:
            print(f"💥 ERROR EN TESTS DE RENDIMIENTO: {e}")
            self.results['performance_tests'] = {
                'executed': True,
                'passed': False,
                'error': str(e)
            }
    
    def check_dependencies(self):
        """Verificar dependencias necesarias para testing"""
        print("🔍 Verificando dependencias de testing...")
        
        dependencies = {
            'requests': 'pip install requests',
            'psutil': 'pip install psutil',
            'selenium': 'pip install selenium'
        }
        
        missing_deps = []
        
        for dep, install_cmd in dependencies.items():
            try:
                __import__(dep)
                print(f"✅ {dep}: Disponible")
            except ImportError:
                print(f"❌ {dep}: No disponible - {install_cmd}")
                missing_deps.append(dep)
        
        if missing_deps:
            print(f"\n⚠️ Dependencias faltantes: {', '.join(missing_deps)}")
            print("💡 Algunos tests pueden ser omitidos")
        else:
            print("✅ Todas las dependencias están disponibles")
        
        return len(missing_deps) == 0
    
    def generate_summary(self):
        """Generar resumen de resultados"""
        total_executed = sum(1 for test in self.results.values() 
                           if isinstance(test, dict) and test.get('executed', False))
        total_passed = sum(1 for test in self.results.values() 
                         if isinstance(test, dict) and test.get('passed', False))
        
        self.results['summary'] = {
            'total_test_suites': 4,
            'executed_test_suites': total_executed,
            'passed_test_suites': total_passed,
            'success_rate': (total_passed / total_executed * 100) if total_executed > 0 else 0
        }
        
        self.results['overall_success'] = total_passed == total_executed and total_executed > 0
    
    def print_final_report(self):
        """Imprimir reporte final"""
        print("\n" + "=" * 80)
        print("📊 REPORTE FINAL DE TESTING")
        print("=" * 80)
        
        # Resumen por tipo de test
        test_types = [
            ('unit_tests', 'Tests Unitarios', '🧪'),
            ('integration_tests', 'Tests de Integración', '🔗'),
            ('e2e_tests', 'Tests End-to-End', '🎭'),
            ('performance_tests', 'Tests de Rendimiento', '🚀')
        ]
        
        for test_key, test_name, emoji in test_types:
            test_result = self.results[test_key]
            if test_result['executed']:
                status = "✅ EXITOSO" if test_result['passed'] else "❌ FALLIDO"
                duration = test_result.get('duration', 0)
                print(f"{emoji} {test_name:25} {status:12} ({duration:.2f}s)")
            else:
                print(f"{emoji} {test_name:25} ⏭️ OMITIDO")
        
        print("-" * 80)
        
        # Estadísticas generales
        summary = self.results['summary']
        print(f"📈 ESTADÍSTICAS GENERALES:")
        print(f"   Suites de test ejecutadas: {summary['executed_test_suites']}/{summary['total_test_suites']}")
        print(f"   Suites exitosas: {summary['passed_test_suites']}/{summary['executed_test_suites']}")
        print(f"   Tasa de éxito: {summary['success_rate']:.1f}%")
        print(f"   Duración total: {self.results['duration']:.2f}s")
        
        print("-" * 80)
        
        # Resultado final
        if self.results['overall_success']:
            print("🎉 RESULTADO FINAL: TODOS LOS TESTS PASARON EXITOSAMENTE")
            print("✅ EL SISTEMA ESTÁ VALIDADO Y LISTO PARA PRODUCCIÓN")
        else:
            print("💥 RESULTADO FINAL: ALGUNOS TESTS FALLARON")
            print("⚠️ REVISAR ERRORES ANTES DE DESPLEGAR EN PRODUCCIÓN")
        
        print("=" * 80)
    
    def save_results_to_file(self):
        """Guardar resultados en archivo JSON"""
        try:
            results_file = os.path.join(os.path.dirname(__file__), 'test_results.json')
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
            print(f"📄 Resultados guardados en: {results_file}")
        except Exception as e:
            print(f"⚠️ No se pudieron guardar los resultados: {e}")
    
    def run_all_tests(self, skip_e2e=False, skip_performance=False):
        """Ejecutar todos los tests"""
        self.results['start_time'] = datetime.now()
        start_time = time.time()
        
        self.print_header()
        
        # Verificar dependencias
        deps_ok = self.check_dependencies()
        
        # Ejecutar cada suite de tests
        self.run_unit_tests_section()
        self.run_integration_tests_section()
        
        if not skip_e2e:
            self.run_e2e_tests_section()
        else:
            print("\n⏭️ TESTS END-TO-END OMITIDOS (skip_e2e=True)")
        
        if not skip_performance:
            self.run_performance_tests_section()
        else:
            print("\n⏭️ TESTS DE RENDIMIENTO OMITIDOS (skip_performance=True)")
        
        # Calcular duración total
        end_time = time.time()
        self.results['end_time'] = datetime.now()
        self.results['duration'] = end_time - start_time
        
        # Generar resumen y reporte final
        self.generate_summary()
        self.print_final_report()
        self.save_results_to_file()
        
        return self.results['overall_success']

def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Ejecutar suite completa de tests')
    parser.add_argument('--skip-e2e', action='store_true', 
                       help='Omitir tests end-to-end (requieren Selenium)')
    parser.add_argument('--skip-performance', action='store_true',
                       help='Omitir tests de rendimiento (pueden ser lentos)')
    parser.add_argument('--unit-only', action='store_true',
                       help='Ejecutar solo tests unitarios')
    parser.add_argument('--integration-only', action='store_true',
                       help='Ejecutar solo tests de integración')
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    if args.unit_only:
        runner.print_header()
        runner.run_unit_tests_section()
        success = runner.results['unit_tests']['passed']
    elif args.integration_only:
        runner.print_header()
        runner.run_integration_tests_section()
        success = runner.results['integration_tests']['passed']
    else:
        success = runner.run_all_tests(
            skip_e2e=args.skip_e2e,
            skip_performance=args.skip_performance
        )
    
    # Código de salida
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()

