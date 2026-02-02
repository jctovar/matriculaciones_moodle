"""Cliente para Moodle REST API."""

import httpx
from .models import Inscripcion


class MoodleError(Exception):
    """Error específico de Moodle API."""

    pass


class MoodleClient:
    """Cliente para interactuar con Moodle REST API."""

    ROLE_STUDENT = 5

    def __init__(self, base_url: str, token: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self._courses_cache: dict[str, dict] | None = None

    async def _call(self, wsfunction: str, **params) -> dict | list:
        """Realiza una llamada a la API de Moodle."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            data = {
                "wstoken": self.token,
                "wsfunction": wsfunction,
                "moodlewsrestformat": "json",
                **params,
            }
            response = await client.post(
                f"{self.base_url}/webservice/rest/server.php",
                data=data,
            )
            response.raise_for_status()
            result = response.json()

            if isinstance(result, dict) and "exception" in result:
                raise MoodleError(f"{result.get('message', 'Error desconocido')}")

            return result

    async def get_user_by_username(self, username: str) -> dict | None:
        """Busca un usuario por su nombre de usuario."""
        result = await self._call(
            "core_user_get_users",
            **{"criteria[0][key]": "username", "criteria[0][value]": username},
        )
        users = result.get("users", [])
        return users[0] if users else None

    async def create_user(self, inscripcion: Inscripcion) -> dict:
        """Crea un nuevo usuario en Moodle."""
        user_data = inscripcion.to_moodle_user()

        params = {}
        for i, (key, value) in enumerate(user_data.items()):
            params[f"users[0][{key}]"] = value

        result = await self._call("core_user_create_users", **params)

        if isinstance(result, list) and len(result) > 0:
            return result[0]
        raise MoodleError("No se pudo crear el usuario")

    async def get_course_by_shortname(self, shortname: str) -> dict | None:
        """Busca un curso por su shortname exacto."""
        result = await self._call(
            "core_course_get_courses_by_field",
            field="shortname",
            value=shortname,
        )
        courses = result.get("courses", [])
        return courses[0] if courses else None

    async def get_all_courses(self) -> list[dict]:
        """Obtiene todos los cursos (con caché)."""
        if self._courses_cache is not None:
            return list(self._courses_cache.values())

        result = await self._call("core_course_get_courses")
        if isinstance(result, list):
            self._courses_cache = {c["shortname"]: c for c in result}
            return result
        return []

    async def find_course_for_group(
        self, asignatura: str, grupo: str
    ) -> dict | None:
        """
        Busca el curso que contenga el grupo del estudiante.

        Los shortnames siguen el patrón: {asignatura}_{grupo1},{grupo2},...
        Ejemplo: 0202_9282,9283 o 0616_9614
        """
        courses = await self.get_all_courses()
        prefix = f"{asignatura}_"

        for course in courses:
            shortname = course.get("shortname", "")
            if not shortname.startswith(prefix):
                continue

            grupos_str = shortname[len(prefix) :]
            grupos_curso = [g.strip() for g in grupos_str.split(",")]

            if grupo in grupos_curso:
                return course

        return None

    async def get_enrolled_users(self, course_id: int) -> list[dict]:
        """Obtiene los usuarios matriculados en un curso."""
        result = await self._call(
            "core_enrol_get_enrolled_users",
            courseid=course_id,
        )
        return result if isinstance(result, list) else []

    async def is_user_enrolled(self, user_id: int, course_id: int) -> bool:
        """Verifica si un usuario está matriculado en un curso."""
        enrolled = await self.get_enrolled_users(course_id)
        return any(u.get("id") == user_id for u in enrolled)

    async def enrol_user(
        self, user_id: int, course_id: int, role_id: int = ROLE_STUDENT
    ) -> bool:
        """Matricula un usuario en un curso con el rol especificado."""
        await self._call(
            "enrol_manual_enrol_users",
            **{
                "enrolments[0][roleid]": role_id,
                "enrolments[0][userid]": user_id,
                "enrolments[0][courseid]": course_id,
            },
        )
        return True
