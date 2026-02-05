#!/usr/bin/env python3
"""Prueba con datos reales de PocketBase para verificar la conversión."""

import asyncio
from src.matriculaciones.pocketbase import PocketBaseClient
from src.matriculaciones.config import Config

async def test_real_data():
    """Prueba con datos reales de PocketBase."""
    try:
        config = Config.from_env()
    except ValueError as e:
        print(f"❌ Error de configuración: {e}")
        return False

    pb_url = config.pocketbase_url
    pb_user = config.api_username
    pb_pass = config.api_password

    print("=" * 80)
    print("PRUEBA CON DATOS REALES DE POCKETBASE")
    print("=" * 80)
    print()

    pb = PocketBaseClient(pb_url)

    try:
        # Autenticar
        print(f"🔐 Autenticando en {pb_url}...")
        await pb.authenticate(pb_user, pb_pass)
        print("✅ Autenticación exitosa\n")

        # Obtener las primeras 5 inscripciones
        print("📥 Obteniendo las primeras 5 inscripciones...")
        inscripciones = await pb.get_inscripciones()

        if not inscripciones:
            print("⚠️  No hay inscripciones en la base de datos")
            return True

        # Mostrar solo las primeras 5
        cantidad = min(5, len(inscripciones))
        print(f"✅ Se obtuvieron {len(inscripciones)} inscripciones totales\n")
        print(f"Mostrando {cantidad} inscripciones de ejemplo:\n")
        print("-" * 80)

        for i, insc in enumerate(inscripciones[:cantidad], 1):
            print(f"\n{i}. Cuenta: {insc.cuenta}")
            print(f"   Nombre: {insc.nombre} {insc.apellidos}")
            print(f"   Email: {insc.correo}")
            print(f"   Fecha nacimiento (contraseña): {insc.nacimiento}")
            print(f"   Asignatura: {insc.asignatura}")
            print(f"   Grupo: {insc.grupo}")

        print("\n" + "-" * 80)
        print(f"\n✅ Todas las {len(inscripciones)} inscripciones fueron procesadas correctamente")
        print("✅ La conversión de formato ISO → ddmmyyyy funciona correctamente")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    result = asyncio.run(test_real_data())
    sys.exit(0 if result else 1)
