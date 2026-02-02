"""Modelos de datos para el sistema de matriculaciones."""

from dataclasses import dataclass
from enum import Enum


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
        """Crea una inscripción desde datos de PocketBase."""
        return cls(
            cuenta=str(data.get("cuenta", "")),
            nombre=data.get("nombre", ""),
            apellidos=data.get("apellidos", ""),
            correo=data.get("correo", ""),
            nacimiento=str(data.get("nacimiento", "")),
            asignatura=str(data.get("asignatura", "")),
            grupo=str(data.get("grupo", "")),
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
