#!/usr/bin/env python3
"""Prueba la conversión de formato ISO a ddmmyyyy."""

from src.matriculaciones.models import Inscripcion


def test_conversion():
    """Prueba con datos reales de PocketBase."""
    # Datos reales de PocketBase
    data_pocketbase = {
        "cuenta": "071172664",
        "nombre": "ISIDRO",
        "apellidos": "MENDEZ LARIOS",
        "correo": "mendez070854@gmail.com",
        "nacimiento": "1954-08-07 00:00:00.000Z",  # Formato ISO de PocketBase
        "asignatura": "1452",
        "grupo": "9404",
    }

    print("=" * 80)
    print("PRUEBA DE CONVERSIÓN ISO 8601 → ddmmyyyy")
    print("=" * 80)
    print()
    print(f"Entrada (PocketBase): {data_pocketbase['nacimiento']}")

    try:
        inscripcion = Inscripcion.from_pocketbase(data_pocketbase)
        print(f"✅ Conversión exitosa!")
        print(f"Formato interno: {inscripcion.nacimiento}")
        print(f"Esperado: 07081954")
        print()

        # Verificar que la conversión sea correcta
        assert inscripcion.nacimiento == "07081954", f"Esperado '07081954', obtenido '{inscripcion.nacimiento}'"
        print("✅ Validación correcta - La fecha coincide")

        # Verificar que se use como contraseña
        user_dict = inscripcion.to_moodle_user()
        print(f"\nContraseña Moodle: {user_dict['password']}")
        print(f"Username Moodle: {user_dict['username']}")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    print("\n" + "=" * 80)
    print("PRUEBA CON FORMATO DIRECTO ddmmyyyy (retrocompatibilidad)")
    print("=" * 80)

    # Probar que también funcione con el formato anterior
    data_directo = {
        "cuenta": "test123",
        "nombre": "Juan",
        "apellidos": "Pérez",
        "correo": "juan@example.com",
        "nacimiento": "15051990",  # Formato ddmmyyyy directo
        "asignatura": "1234",
        "grupo": "9999",
    }

    try:
        inscripcion2 = Inscripcion.from_pocketbase(data_directo)
        print(f"✅ Formato directo también funciona: {inscripcion2.nacimiento}")
    except Exception as e:
        print(f"❌ Error con formato directo: {e}")
        return False

    print("\n✅ Todas las pruebas pasaron correctamente")
    return True


if __name__ == "__main__":
    import sys
    sys.exit(0 if test_conversion() else 1)
