"""Cliente para Moodle REST API."""

import asyncio
import logging
import re
import httpx
from .models import Inscripcion

logger = logging.getLogger(__name__)


class MoodleError(Exception):
    """Error específico de Moodle API."""

    pass


class MoodleClient:
    """Cliente para interactuar con Moodle REST API."""

    ROLE_STUDENT = 5

    def __init__(self, base_url: str, token: str, timeout: float = 30.0, max_concurrent: int = 10):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self._courses_cache: dict[str, dict] | None = None
        self._course_prefix_index: dict[str, list[dict]] | None = None
        self._enrollment_cache: dict[int, set[int]] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)

    @staticmethod
    def _validate_username(username: str) -> str:
        """Valida y sanitiza un nombre de usuario."""
        if not username:
            raise ValueError("Username no puede estar vacío")

        if len(username) > 100:
            raise ValueError("Username excede longitud máxima (100 caracteres)")

        # Solo permitir caracteres alfanuméricos, guiones, puntos y guiones bajos
        if not re.match(r'^[a-zA-Z0-9._-]+$', username):
            raise ValueError(f"Username contiene caracteres no permitidos: {username}")

        return username.strip()

    @staticmethod
    def _validate_positive_int(value: int, name: str) -> int:
        """Valida que un valor sea un entero positivo."""
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} debe ser un entero positivo, recibido: {value}")
        return value

    async def _call(self, wsfunction: str, **params) -> dict | list:
        """Realiza una llamada a la API de Moodle con rate limiting."""
        logger.debug(f"Llamando API Moodle: {wsfunction} con params: {list(params.keys())}")

        async with self._semaphore:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                verify=True,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            ) as client:
                data = {
                    "wstoken": self.token,
                    "wsfunction": wsfunction,
                    "moodlewsrestformat": "json",
                    **params,
                }

                try:
                    response = await client.post(
                        f"{self.base_url}/webservice/rest/server.php",
                        data=data,
                    )
                    response.raise_for_status()
                    result = response.json()

                    if isinstance(result, dict) and "exception" in result:
                        error_msg = result.get('message', 'Error desconocido')
                        logger.error(f"Error en {wsfunction}: {error_msg}")
                        raise MoodleError(error_msg)

                    logger.debug(f"Llamada exitosa a {wsfunction}")
                    return result

                except httpx.HTTPStatusError as e:
                    logger.error(f"HTTP error en {wsfunction}: {e.response.status_code} - {e.response.text[:200]}")
                    raise MoodleError(f"Error HTTP {e.response.status_code}: {e.response.text[:100]}")
                except httpx.RequestError as e:
                    logger.error(f"Error de conexión en {wsfunction}: {str(e)}")
                    raise MoodleError(f"Error de conexión: {str(e)}")

    async def get_user_by_username(self, username: str) -> dict | None:
        """Busca un usuario por su nombre de usuario."""
        validated_username = self._validate_username(username)
        logger.info(f"Buscando usuario: {validated_username}")

        result = await self._call(
            "core_user_get_users",
            **{"criteria[0][key]": "username", "criteria[0][value]": validated_username},
        )

        if not isinstance(result, dict):
            logger.error(f"Respuesta inesperada de Moodle: tipo {type(result)}")
            return None

        users = result.get("users", [])
        if users:
            logger.info(f"Usuario encontrado: {validated_username} (ID: {users[0].get('id')})")
        else:
            logger.info(f"Usuario no encontrado: {validated_username}")
        return users[0] if users else None

    async def batch_get_users(self, usernames: list[str]) -> dict[str, dict | None]:
        """Busca múltiples usuarios en paralelo."""
        if not usernames:
            return {}

        logger.info(f"Buscando {len(usernames)} usuarios en lote")
        tasks = [self.get_user_by_username(u) for u in usernames]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        user_map = {}
        for username, result in zip(usernames, results):
            if isinstance(result, Exception):
                logger.warning(f"Error buscando usuario {username}: {result}")
                user_map[username] = None
            else:
                user_map[username] = result

        found = sum(1 for v in user_map.values() if v is not None)
        logger.info(f"Usuarios encontrados: {found}/{len(usernames)}")
        return user_map

    async def create_user(self, inscripcion: Inscripcion) -> dict:
        """Crea un nuevo usuario en Moodle."""
        logger.info(f"Creando usuario: {inscripcion.cuenta} ({inscripcion.correo})")
        user_data = inscripcion.to_moodle_user()

        params = {}
        for i, (key, value) in enumerate(user_data.items()):
            params[f"users[0][{key}]"] = value

        result = await self._call("core_user_create_users", **params)

        if isinstance(result, list) and len(result) > 0:
            user_id = result[0].get('id')
            logger.info(f"Usuario creado exitosamente: {inscripcion.cuenta} (ID: {user_id})")
            return result[0]

        logger.error(f"Error al crear usuario {inscripcion.cuenta}: respuesta inválida")
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
            self._build_prefix_index(result)
            return result
        return []

    def _build_prefix_index(self, courses: list[dict]) -> None:
        """Construye índice por prefijo de asignatura para búsqueda O(1)."""
        self._course_prefix_index = {}
        for course in courses:
            shortname = course.get("shortname", "")
            if "_" not in shortname:
                continue
            prefix = shortname.split("_")[0]
            if prefix not in self._course_prefix_index:
                self._course_prefix_index[prefix] = []
            self._course_prefix_index[prefix].append(course)

    async def find_course_for_group(
        self, asignatura: str, grupo: str
    ) -> dict | None:
        """
        Busca el curso que contenga el grupo del estudiante.

        Los shortnames siguen el patrón: {asignatura}_{grupo1},{grupo2},...
        Ejemplo: 0202_9282,9283 o 0616_9614
        """
        await self.get_all_courses()

        if self._course_prefix_index is None:
            return None

        candidates = self._course_prefix_index.get(asignatura, [])
        for course in candidates:
            shortname = course.get("shortname", "")
            grupos_str = shortname.split("_", 1)[1] if "_" in shortname else ""
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

    async def _populate_enrollment_cache(self, course_id: int) -> None:
        """Puebla el caché de matriculaciones para un curso."""
        if course_id in self._enrollment_cache:
            return

        logger.debug(f"Poblando caché de matriculaciones para curso {course_id}")
        enrolled = await self.get_enrolled_users(course_id)
        self._enrollment_cache[course_id] = {u.get("id") for u in enrolled if u.get("id")}
        logger.debug(f"Caché poblado: {len(self._enrollment_cache[course_id])} usuarios en curso {course_id}")

    async def is_user_enrolled(self, user_id: int, course_id: int) -> bool:
        """Verifica si un usuario está matriculado en un curso usando caché."""
        self._validate_positive_int(user_id, "user_id")
        self._validate_positive_int(course_id, "course_id")

        if course_id not in self._enrollment_cache:
            await self._populate_enrollment_cache(course_id)

        is_enrolled = user_id in self._enrollment_cache[course_id]
        logger.debug(f"Usuario {user_id} {'está' if is_enrolled else 'NO está'} matriculado en curso {course_id} (caché)")
        return is_enrolled

    async def batch_check_enrollments(self, user_course_pairs: list[tuple[int, int]]) -> dict[tuple[int, int], bool]:
        """Verifica múltiples matriculaciones en lote.

        Args:
            user_course_pairs: Lista de tuplas (user_id, course_id)

        Returns:
            Diccionario con {(user_id, course_id): is_enrolled}
        """
        course_ids = {course_id for _, course_id in user_course_pairs}

        tasks = [
            self._populate_enrollment_cache(course_id)
            for course_id in course_ids
            if course_id not in self._enrollment_cache
        ]

        if tasks:
            await asyncio.gather(*tasks)

        return {
            (user_id, course_id): user_id in self._enrollment_cache[course_id]
            for user_id, course_id in user_course_pairs
        }

    async def enrol_user(
        self, user_id: int, course_id: int, role_id: int = ROLE_STUDENT
    ) -> bool:
        """Matricula un usuario en un curso con el rol especificado."""
        self._validate_positive_int(user_id, "user_id")
        self._validate_positive_int(course_id, "course_id")
        self._validate_positive_int(role_id, "role_id")

        logger.info(f"Matriculando usuario {user_id} en curso {course_id} con rol {role_id}")

        await self._call(
            "enrol_manual_enrol_users",
            **{
                "enrolments[0][roleid]": role_id,
                "enrolments[0][userid]": user_id,
                "enrolments[0][courseid]": course_id,
            },
        )

        if course_id in self._enrollment_cache:
            self._enrollment_cache[course_id].add(user_id)

        logger.info(f"Usuario {user_id} matriculado exitosamente en curso {course_id}")
        return True

    async def batch_enrol_users(
        self, enrolments: list[tuple[int, int]], role_id: int = ROLE_STUDENT
    ) -> dict[tuple[int, int], bool]:
        """Matricula múltiples usuarios en un solo API call.

        Args:
            enrolments: Lista de tuplas (user_id, course_id)
            role_id: Rol a asignar (default: estudiante)

        Returns:
            Diccionario {(user_id, course_id): success}
        """
        if not enrolments:
            return {}

        logger.info(f"Matriculando {len(enrolments)} usuarios en lote")

        params = {}
        for i, (user_id, course_id) in enumerate(enrolments):
            self._validate_positive_int(user_id, f"user_id[{i}]")
            self._validate_positive_int(course_id, f"course_id[{i}]")
            params[f"enrolments[{i}][roleid]"] = role_id
            params[f"enrolments[{i}][userid]"] = user_id
            params[f"enrolments[{i}][courseid]"] = course_id

        try:
            await self._call("enrol_manual_enrol_users", **params)
            for user_id, course_id in enrolments:
                if course_id in self._enrollment_cache:
                    self._enrollment_cache[course_id].add(user_id)
            logger.info(f"Lote de {len(enrolments)} matriculaciones completado")
            return {pair: True for pair in enrolments}
        except MoodleError as e:
            logger.error(f"Error en batch enrol: {e}")
            return {pair: False for pair in enrolments}
