#!/usr/bin/env python3
"""Script de prueba para validar el formato de fecha de nacimiento."""

from src.matriculaciones.models import Inscripcion


def test_fecha(data: dict, descripcion: str) -> None:
    """Prueba una fecha y muestra el resultado."""
    try:
        inscripcion = Inscripcion.from_pocketbase(data)
        print(f"✅ {descripcion}: '{data['nacimiento']}' - VÁLIDO")
        print(f"   Contraseña generada: {inscripcion.nacimiento}")
    except ValueError as e:
        print(f"❌ {descripcion}: '{data['nacimiento']}' - RECHAZADO")
        print(f"   Error: {str(e)}")
    print()


if __name__ == "__main__":
    # Datos base válidos
    base_data = {
        "cuenta": "test123",
        "nombre": "Juan",
        "apellidos": "Pérez López",
        "correo": "juan@example.com",
        "asignatura": "0202",
        "grupo": "9282",
    }

    print("=" * 80)
    print("PRUEBAS DE VALIDACIÓN DE FECHA DE NACIMIENTO (ddmmyyyy)")
    print("=" * 80)
    print()

    print("🧪 CASOS VÁLIDOS:")
    print("-" * 80)

    test_fecha(
        {**base_data, "nacimiento": "15051990"},
        "Fecha estándar"
    )

    test_fecha(
        {**base_data, "nacimiento": "01012000"},
        "Con ceros iniciales"
    )

    test_fecha(
        {**base_data, "nacimiento": "29022000"},
        "29 de febrero (año bisiesto)"
    )

    test_fecha(
        {**base_data, "nacimiento": "31121995"},
        "Último día del año"
    )

    test_fecha(
        {**base_data, "nacimiento": "01011990"},
        "Primer día del año"
    )

    print("\n🧪 CASOS INVÁLIDOS - Formato incorrecto:")
    print("-" * 80)

    test_fecha(
        {**base_data, "nacimiento": "1990-05-15"},
        "Formato yyyy-mm-dd"
    )

    test_fecha(
        {**base_data, "nacimiento": "15/05/1990"},
        "Con separadores /"
    )

    test_fecha(
        {**base_data, "nacimiento": "15-05-1990"},
        "Con separadores -"
    )

    test_fecha(
        {**base_data, "nacimiento": "150590"},
        "Solo 6 dígitos"
    )

    test_fecha(
        {**base_data, "nacimiento": "15051990 "},
        "Con espacio al final"
    )

    test_fecha(
        {**base_data, "nacimiento": "abcd1990"},
        "Con letras"
    )

    test_fecha(
        {**base_data, "nacimiento": ""},
        "Vacío"
    )

    print("\n🧪 CASOS INVÁLIDOS - Fechas imposibles:")
    print("-" * 80)

    test_fecha(
        {**base_data, "nacimiento": "32011990"},
        "Día 32 (no existe)"
    )

    test_fecha(
        {**base_data, "nacimiento": "00011990"},
        "Día 0"
    )

    test_fecha(
        {**base_data, "nacimiento": "15131990"},
        "Mes 13 (no existe)"
    )

    test_fecha(
        {**base_data, "nacimiento": "15001990"},
        "Mes 0"
    )

    test_fecha(
        {**base_data, "nacimiento": "29022001"},
        "29 de febrero (año NO bisiesto)"
    )

    test_fecha(
        {**base_data, "nacimiento": "31041990"},
        "31 de abril (no existe)"
    )

    test_fecha(
        {**base_data, "nacimiento": "15051899"},
        "Año 1899 (fuera de rango)"
    )

    test_fecha(
        {**base_data, "nacimiento": "15052025"},
        "Año 2025 (fuera de rango)"
    )

    print("=" * 80)
    print("FIN DE PRUEBAS")
    print("=" * 80)
