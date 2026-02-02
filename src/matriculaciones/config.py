"""Configuración y carga de variables de entorno."""

from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv
import os


@dataclass
class Config:
    """Configuración del sistema."""

    pocketbase_url: str
    api_username: str
    api_password: str
    moodle_url: str
    moodle_token: str

    @classmethod
    def from_env(cls, env_path: Path | None = None) -> "Config":
        """Carga configuración desde variables de entorno."""
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()

        required_vars = [
            "POCKETBASE_URL",
            "API_USERNAME",
            "API_PASSWORD",
            "MOODLE_URL",
            "MOODLE_TOKEN",
        ]

        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ValueError(f"Variables de entorno faltantes: {', '.join(missing)}")

        return cls(
            pocketbase_url=os.getenv("POCKETBASE_URL", ""),
            api_username=os.getenv("API_USERNAME", ""),
            api_password=os.getenv("API_PASSWORD", ""),
            moodle_url=os.getenv("MOODLE_URL", ""),
            moodle_token=os.getenv("MOODLE_TOKEN", ""),
        )
