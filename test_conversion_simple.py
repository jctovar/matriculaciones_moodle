#!/usr/bin/env python3
"""Test simple de conversión sin dependencias externas."""

import sys
import os

# Agregar el directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from matriculaciones.models import Inscripcion

def test_conversion_iso():
    """Prueba la conversión con formato ISO como viene de PocketBase."""

    print("=" * 80)
    print("TEST DE CONVERSIÓN DE FORMATO ISO → ddmmyyyy")
    print("=" * 80)
    print()

    # Datos de ejemplo como vienen de PocketBase
    casos_prueba = [
        {
            "cuenta": "071172664",
            "nombre": "ISIDRO",
            "apellidos": "MENDEZ LARIOS",
            "correo": "mendez070854@gmail.com",
            "nacimiento": "1954-08-07 00:00:00.000Z",
            "asignatura": "1452",
            "grupo": "9404",
            "esperado": "07081954"
        },
        {
            "cuenta": "073210304",
            "nombre": "CARLOS ERNESTO",
            "apellidos": "LUYANDO AGUIRRE",
            "correo": "carlosluyando@yahoo.com",
            "nacimiento": "1957-07-13 00:00:00.000Z",
            "asignatura": "1251",
            "grupo": "9219",
            "esperado": "13071957"
        },
    ]

    errores = 0

    for i, caso in enumerate(casos_prueba, 1):
        print(f"Caso {i}:")
        print(f"  Cuenta: {caso['cuenta']}")
        print(f"  Nacimiento ISO: {caso['nacimiento']}")
        print(f"  Esperado ddmmyyyy: {caso['esperado']}")

        try:
            inscripcion = Inscripcion.from_pocketbase(caso)

            if inscripcion.nacimiento == caso['esperado']:
                print(f"  ✅ Conversión correcta: {inscripcion.nacimiento}")
            else:
                print(f"  ❌ Error: se esperaba {caso['esperado']}, se obtuvo {inscripcion.nacimiento}")
                errores += 1

        except Exception as e:
            print(f"  ❌ Error: {e}")
            errores += 1

        print()

    print("=" * 80)
    if errores == 0:
        print("✅ TODOS LOS TESTS PASARON")
        return True
    else:
        print(f"❌ {errores} TEST(S) FALLARON")
        return False

if __name__ == "__main__":
    success = test_conversion_iso()
    sys.exit(0 if success else 1)
