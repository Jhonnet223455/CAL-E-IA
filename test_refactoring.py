"""
Script de prueba rápida para validar la refactorización.
Verifica que todos los módulos se importen correctamente.
"""

import sys
import os

# Añadir el directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Prueba que todos los módulos se importen correctamente."""
    print("🧪 Iniciando pruebas de importación...\n")
    
    success_count = 0
    fail_count = 0
    
    # Test 1: database.py
    try:
        from database import (
            init_database,
            save_message,
            get_chat_history,
            clear_old_history,
            delete_user_history
        )
        print("✅ database.py - Todas las funciones importadas correctamente")
        print(f"   - init_database: {callable(init_database)}")
        print(f"   - save_message: {callable(save_message)}")
        print(f"   - get_chat_history: {callable(get_chat_history)}")
        print(f"   - clear_old_history: {callable(clear_old_history)}")
        print(f"   - delete_user_history: {callable(delete_user_history)}")
        success_count += 1
    except Exception as e:
        print(f"❌ database.py - Error: {e}")
        fail_count += 1
    
    print()
    
    # Test 2: weather_tools.py
    try:
        from weather_tools import (
            obtener_clima_por_latlng,
            clima_por_lugar,
            tool_clima_por_lugar
        )
        print("✅ weather_tools.py - Todas las funciones importadas correctamente")
        print(f"   - obtener_clima_por_latlng: {callable(obtener_clima_por_latlng)}")
        print(f"   - clima_por_lugar: {callable(clima_por_lugar)}")
        print(f"   - tool_clima_por_lugar: {tool_clima_por_lugar.name}")
        success_count += 1
    except Exception as e:
        print(f"❌ weather_tools.py - Error: {e}")
        fail_count += 1
    
    print()
    
    # Test 3: places_tools.py
    try:
        from places_tools import (
            buscar_lugares_google,
            tool_google_places
        )
        print("✅ places_tools.py - Todas las funciones importadas correctamente")
        print(f"   - buscar_lugares_google: {callable(buscar_lugares_google)}")
        print(f"   - tool_google_places: {tool_google_places.name}")
        success_count += 1
    except Exception as e:
        print(f"❌ places_tools.py - Error: {e}")
        fail_count += 1
    
    print()
    
    # Test 4: prompts.py
    try:
        from prompts import AGENT_PROMPT_TEMPLATE
        print("✅ prompts.py - Template importado correctamente")
        print(f"   - Longitud del prompt: {len(AGENT_PROMPT_TEMPLATE)} caracteres")
        print(f"   - Contiene 'CAL-E': {('CAL-E' in AGENT_PROMPT_TEMPLATE)}")
        success_count += 1
    except Exception as e:
        print(f"❌ prompts.py - Error: {e}")
        fail_count += 1
    
    print()
    
    # Test 5: main.py (solo verificar sintaxis)
    try:
        import main
        print("✅ main.py - Se importa sin errores de sintaxis")
        success_count += 1
    except Exception as e:
        print(f"❌ main.py - Error: {e}")
        fail_count += 1
    
    print("\n" + "="*60)
    print(f"📊 RESULTADOS:")
    print(f"   ✅ Exitosos: {success_count}/5")
    print(f"   ❌ Fallidos: {fail_count}/5")
    
    if fail_count == 0:
        print("\n🎉 ¡Todas las pruebas pasaron! La refactorización es exitosa.")
        return True
    else:
        print("\n⚠️  Hay errores que necesitan ser corregidos.")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 PRUEBA DE REFACTORIZACIÓN - BOT CAL-E")
    print("=" * 60)
    print()
    
    result = test_imports()
    
    sys.exit(0 if result else 1)
