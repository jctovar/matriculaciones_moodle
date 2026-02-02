"""Cliente para PocketBase API."""

import httpx
from .models import Inscripcion


class PocketBaseClient:
    """Cliente para interactuar con PocketBase."""

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.token: str | None = None
        self.timeout = timeout

    async def authenticate(self, email: str, password: str) -> str:
        """Autenticarse con PocketBase como superusuario."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # PocketBase v0.23+ usa _superusers como colección de admins
            endpoints = [
                f"{self.base_url}/api/collections/_superusers/auth-with-password",
                f"{self.base_url}/api/admins/auth-with-password",
                f"{self.base_url}/api/collections/users/auth-with-password",
            ]

            last_error = None
            for endpoint in endpoints:
                response = await client.post(
                    endpoint,
                    json={"identity": email, "password": password},
                )
                if response.status_code == 200:
                    data = response.json()
                    self.token = data["token"]
                    return self.token
                last_error = response

            if last_error:
                last_error.raise_for_status()
            raise Exception("No se pudo autenticar con ningún endpoint")

    async def get_inscripciones(self) -> list[Inscripcion]:
        """Obtiene todas las inscripciones de la vista reporte_inscripciones."""
        if not self.token:
            raise ValueError("No autenticado. Llame a authenticate() primero.")

        inscripciones: list[Inscripcion] = []
        page = 1
        per_page = 500

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while True:
                response = await client.get(
                    f"{self.base_url}/api/collections/reporte_inscripciones/records",
                    headers={"Authorization": f"Bearer {self.token}"},
                    params={"page": page, "perPage": per_page},
                )
                response.raise_for_status()
                data = response.json()

                for item in data.get("items", []):
                    inscripciones.append(Inscripcion.from_pocketbase(item))

                if page >= data.get("totalPages", 1):
                    break
                page += 1

        return inscripciones
