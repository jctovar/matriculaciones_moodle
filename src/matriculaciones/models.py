"""Modelos de datos para el sistema de matriculaciones."""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


def _validate_field(
    value: str | None,
    name: str,
    max_len: int = 100,
    pattern: str | None = None,
    pattern_error: str | None = None,
) -> str:
    """Valida un campo de texto requerido."""
    value = str(value or "").strip()
    if not value:
        raise ValueError(f"Campo '{name}' es requerido")
    if len(value) > max_len:
        raise ValueError(f"Campo '{name}' excede longitud máxima: {value}")
    if pattern and not re.match(pattern, value):
        raise ValueError(pattern_error or f"Campo '{name}' tiene formato inválido: {value}")
    return value


def _parse_birthdate(raw: str) -> str:
    """Convierte fecha a formato ddmmyyyy. Acepta ISO 8601 o ddmmyyyy."""
    # ISO 8601: "1954-08-07 00:00:00.000Z" -> "07081954"
    if re.match(r'^\d{4}-\d{2}-\d{2}', raw):
        try:
            fecha = datetime.strptime(raw.split()[0], "%Y-%m-%d")
            return fecha.strftime("%d%m%Y")
        except ValueError as e:
            raise ValueError(f"Fecha ISO inválida '{raw}': {e}")

    if not re.match(r'^\d{8}$', raw):
        raise ValueError(f"Campo 'nacimiento' debe tener formato ddmmyyyy: '{raw}'")

    try:
        fecha = datetime.strptime(raw, "%d%m%Y")
    except ValueError:
        raise ValueError(f"Fecha de nacimiento inválida '{raw}'")

    if not (1900 <= fecha.year <= 2020):
        raise ValueError(f"Año fuera de rango válido (1900-2020): {fecha.year}")

    return raw


class EstadoMatriculacion(Enum):
    """Estados posibles de una matriculación."""

    EXITO = "exito"
    YA_MATRICULADO = "ya_matriculado"
    USUARIO_CREADO = "usuario_creado"
    ERROR_CURSO_NO_ENCONTRADO = "error_curso_no_encontrado"
    ERROR_USUARIO = "error_usuario"
    ERROR_MATRICULACION = "error_matriculacion"
    ERROR_CONEXION = "error_conexion"


@dataclass
class Inscripcion:
    """Datos de inscripción desde PocketBase."""

    cuenta: str
    nombre: str
    apellidos: str
    correo: str
    nacimiento: str
    asignatura: str
    grupo: str

    @classmethod
    def from_pocketbase(cls, data: dict) -> "Inscripcion":
        """Crea una inscripción desde datos de PocketBase con validación."""
        cuenta = _validate_field(data.get("cuenta"), "cuenta")
        nombre = _validate_field(data.get("nombre"), "nombre")
        apellidos = _validate_field(data.get("apellidos"), "apellidos")
        correo = _validate_field(
            data.get("correo"),
            "correo",
            pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            pattern_error=f"Email inválido: {data.get('correo')}",
        )

        nacimiento_raw = str(data.get("nacimiento", "")).strip()
        if not nacimiento_raw:
            raise ValueError("Campo 'nacimiento' es requerido")

        nacimiento = _parse_birthdate(nacimiento_raw)

        asignatura = _validate_field(data.get("asignatura"), "asignatura", max_len=50)
        grupo = _validate_field(data.get("grupo"), "grupo", max_len=50)

        return cls(
            cuenta=cuenta,
            nombre=nombre,
            apellidos=apellidos,
            correo=correo,
            nacimiento=nacimiento,
            asignatura=asignatura,
            grupo=grupo,
        )

    def to_moodle_user(self) -> dict:
        """Convierte a formato de usuario Moodle."""
        return {
            "username": self.cuenta,
            "firstname": self.nombre,
            "lastname": self.apellidos,
            "email": self.correo,
            "password": self.nacimiento,
            "idnumber": self.cuenta,
            "city": "Tlalnepantla de Baz",
            "country": "MX",
            "institution": "FES Iztacala",
            "department": "PSICOLOGIA",
        }


@dataclass
class ResultadoMatriculacion:
    """Resultado de una operación de matriculación."""

    inscripcion: Inscripcion
    estado: EstadoMatriculacion
    mensaje: str = ""
    user_id: int | None = None
    course_id: int | None = None
