"""Cliente para PocketBase API."""

import asyncio
import logging
import httpx
from .models import Inscripcion

logger = logging.getLogger(__name__)


class PocketBaseError(Exception):
    """Error específico de PocketBase API."""

    pass


class PocketBaseClient:
    """Cliente para interactuar con PocketBase."""

    def __init__(self, base_url: str, timeout: float = 30.0, max_concurrent: int = 5):
        self.base_url = base_url.rstrip("/")
        self.token: str | None = None
        self.timeout = timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def authenticate(self, email: str, password: str) -> str:
        """Autenticarse con PocketBase como superusuario."""
        logger.info(f"Autenticando con PocketBase: {email}")

        async with self._semaphore:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                verify=True,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            ) as client:
                # PocketBase v0.23+ usa _superusers como colección de admins
                endpoints = [
                    f"{self.base_url}/api/collections/_superusers/auth-with-password",
                    f"{self.base_url}/api/admins/auth-with-password",
                    f"{self.base_url}/api/collections/users/auth-with-password",
                ]

                errors = []
                for endpoint in endpoints:
                    endpoint_name = endpoint.split('/')[-2]
                    logger.debug(f"Intentando autenticación en: {endpoint_name}")

                    try:
                        response = await client.post(
                            endpoint,
                            json={"identity": email, "password": password},
                        )

                        if response.status_code == 200:
                            data = response.json()

                            if "token" not in data:
                                error_msg = f"{endpoint_name}: Respuesta sin token"
                                logger.warning(error_msg)
                                errors.append(error_msg)
                                continue

                            self.token = data["token"]
                            logger.info(f"Autenticación exitosa en: {endpoint_name}")
                            return self.token

                        error_msg = f"{endpoint_name}: HTTP {response.status_code} - {response.text[:100]}"
                        logger.debug(error_msg)
                        errors.append(error_msg)

                    except httpx.HTTPError as e:
                        error_msg = f"{endpoint_name}: {type(e).__name__} - {str(e)}"
                        logger.debug(error_msg)
                        errors.append(error_msg)

                error_summary = "; ".join(errors)
                logger.error(f"Falló autenticación en todos los endpoints: {error_summary}")
                raise PocketBaseError(f"No se pudo autenticar con ningún endpoint: {error_summary}")

    async def get_inscripciones(self) -> list[Inscripcion]:
        """Obtiene todas las inscripciones de la vista reporte_inscripciones."""
        if not self.token:
            logger.error("Intento de obtener inscripciones sin autenticación")
            raise PocketBaseError("No autenticado. Llame a authenticate() primero.")

        logger.info("Descargando inscripciones de PocketBase")
        per_page = 500
        url = f"{self.base_url}/api/collections/reporte_inscripciones/records"
        headers = {"Authorization": f"Bearer {self.token}"}

        async with httpx.AsyncClient(
            timeout=self.timeout,
            verify=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        ) as client:
            try:
                # Primera petición para obtener total de páginas
                response = await client.get(url, headers=headers, params={"page": 1, "perPage": per_page})
                response.raise_for_status()
                first_data = response.json()
                total_pages = first_data.get("totalPages", 1)
                logger.debug(f"Total páginas a descargar: {total_pages}")

                if total_pages == 1:
                    return self._parse_items(first_data.get("items", []))

                # Descargar resto de páginas en paralelo
                async def fetch_page(page: int) -> list[dict]:
                    async with self._semaphore:
                        resp = await client.get(url, headers=headers, params={"page": page, "perPage": per_page})
                        resp.raise_for_status()
                        return resp.json().get("items", [])

                tasks = [fetch_page(p) for p in range(2, total_pages + 1)]
                results = await asyncio.gather(*tasks)

                all_items = first_data.get("items", [])
                for items in results:
                    all_items.extend(items)

                inscripciones = self._parse_items(all_items)
                logger.info(f"Total de inscripciones descargadas: {len(inscripciones)}")
                return inscripciones

            except httpx.HTTPError as e:
                logger.error(f"Error HTTP al descargar inscripciones: {str(e)}")
                raise PocketBaseError(f"Error al descargar inscripciones: {str(e)}")

    def _parse_items(self, items: list[dict]) -> list[Inscripcion]:
        """Parsea items de PocketBase a Inscripciones."""
        inscripciones = []
        for item in items:
            try:
                inscripciones.append(Inscripcion.from_pocketbase(item))
            except Exception as e:
                logger.warning(f"Error procesando inscripción {item.get('id', 'unknown')}: {e}")
        return inscripciones
