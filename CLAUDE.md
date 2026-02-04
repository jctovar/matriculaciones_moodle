# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Descripción del Proyecto

Script CLI en Python para automatizar matriculaciones de estudiantes en cursos Moodle. Conecta PocketBase (fuente de datos de inscripciones) con la API REST de Moodle.

## Stack Tecnológico

- **Lenguaje:** Python
- **Gestor de dependencias:** UV
- **Backend de datos:** PocketBase
- **Sistema destino:** Moodle REST API

## Comandos de Desarrollo

```bash
# Instalar dependencias
uv sync

# Ejecutar el script principal
uv run python main.py

# Ejecutar con UV directamente (si está configurado como CLI)
uv run matriculaciones
```

## Arquitectura

### Flujo de Ejecución

1. Autenticar con PocketBase
2. Descargar registros de la vista `reporte_inscripciones`
3. Por cada registro:
   - Localizar curso en Moodle usando `asignatura_grupo` como shortname
   - Verificar si el usuario ya está matriculado
   - Matricular con rol 'student' si no existe
4. Generar reporte de resultados

### APIs Externas

**PocketBase:** `https://pocket.fanguye.com`
- Vista principal: `reporte_inscripciones`

**Moodle REST API:** `{MOODLE_URL}/webservice/rest/server.php`
- Funciones principales: `core_user_create_users`, `enrol_manual_enrol_users`, `core_course_get_courses_by_field`

### Mapeo de Campos PocketBase → Moodle

| PocketBase | Moodle |
|-----------|--------|
| cuenta | username, idnumber |
| nombre | firstname |
| apellidos | lastname |
| correo | email |
| nacimiento | password |
| asignatura | course (shortname) |
| grupo | group1 |

Valores fijos: `city='Tlalnepantla de Baz'`, `country='MX'`, `institution='FES Iztacala'`, `department='PSICOLOGIA'`

### Nomenclatura de Cursos Moodle

Shortnames siguen el patrón: `{asignatura}_{grupo1},{grupo2},...`

Ejemplos: `0202_9282,9283`, `0616_9614`, `1153_9121,9122,9123`

## Variables de Entorno (.env)

```
API_USERNAME=     # Usuario PocketBase
API_PASSWORD=     # Contraseña PocketBase
POCKETBASE_URL=   # URL de PocketBase
MOODLE_URL=       # URL base de Moodle
MOODLE_TOKEN=     # Token de servicio web Moodle
```

## Referencias

- Documentación de API Moodle: `api_reference.md` (referencia local completa)
- https://docs.moodle.org/dev/Creating_a_web_service_client
