# Matriculaciones Moodle

Script CLI en Python para automatizar matriculaciones de estudiantes en cursos Moodle, obteniendo datos desde PocketBase.

## Descripción

Este proyecto automatiza el proceso de matriculación de estudiantes en Moodle:

1. Autentica con PocketBase
2. Descarga registros de inscripciones de la vista `reporte_inscripciones`
3. Por cada inscripción:
   - Localiza o crea el usuario en Moodle
   - Busca el curso usando el patrón `{asignatura}_{grupos}`
   - Verifica si ya está matriculado
   - Realiza la matriculación si es necesario
4. Genera reporte visual con estadísticas

## Stack Tecnológico

- **Lenguaje:** Python 3.11+
- **Gestor de dependencias:** [UV](https://github.com/astral-sh/uv)
- **Cliente HTTP:** httpx (async)
- **Interfaz CLI:** Rich
- **Carga de configuración:** python-dotenv

## Instalación

### Requisitos previos

- Python 3.11 o superior
- UV (gestor de dependencias)

### Pasos de instalación

```bash
# Clonar el repositorio
git clone <repo-url>
cd matriculaciones_moodle

# Instalar dependencias
uv sync
```

## Configuración

Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:

```env
API_USERNAME=       # Correo del usuario/admin PocketBase
API_PASSWORD=       # Contraseña del usuario/admin PocketBase
POCKETBASE_URL=     # URL de PocketBase (ej: https://pocket.example.com)
MOODLE_URL=         # URL base de Moodle (ej: https://moodle.example.com/2026-2)
MOODLE_TOKEN=       # Token de acceso a API REST de Moodle
```

## Uso

```bash
# Ejecutar el script
uv run matriculaciones

# O si el proyecto está instalado en editable mode
matriculaciones
```

El script mostrará:
- Spinner mientras se conecta a PocketBase
- Spinner mientras carga los cursos de Moodle
- Barra de progreso con el procesamiento de inscripciones
- Tabla resumen con estadísticas
- Tabla detallada de errores (si los hay)

## Arquitectura

### Módulos principales

#### `config.py`
Carga y valida variables de entorno. Define la clase `Config` con todos los parámetros necesarios.

#### `models.py`
Define estructuras de datos:
- `Inscripcion`: Datos de PocketBase
- `ResultadoMatriculacion`: Resultado de cada operación
- `EstadoMatriculacion`: Estados posibles (éxito, error, ya matriculado, etc.)

#### `pocketbase.py`
Cliente para interactuar con PocketBase:
- `authenticate()`: Autenticación como superusuario
- `get_inscripciones()`: Descarga registros con paginación

Soporta múltiples versiones de PocketBase probando diferentes endpoints de autenticación.

#### `moodle.py`
Cliente para Moodle REST API:
- `get_user_by_username()`: Busca usuario existente
- `create_user()`: Crea nuevo usuario con mapeo de campos
- `get_course_by_shortname()`: Busca curso exacto
- `get_all_courses()`: Caché de todos los cursos
- `find_course_for_group()`: Busca curso que contenga el grupo
- `is_user_enrolled()`: Verifica matriculación
- `enrol_user()`: Matricula usuario con rol student

#### `main.py`
Orquestación del flujo principal y generación de reportes visuales con Rich.

## Mapeo de Campos PocketBase → Moodle

| PocketBase | Moodle | Descripción |
|-----------|--------|-------------|
| cuenta | username, idnumber | Identificador único del usuario |
| nombre | firstname | Nombre |
| apellidos | lastname | Apellidos |
| correo | email | Correo electrónico |
| nacimiento | password | Se usa como contraseña inicial |
| asignatura | course shortname | Primera parte del shortname |
| grupo | course shortname | Segunda parte del shortname |

**Valores fijos asignados automáticamente:**
- city: `Tlalnepantla de Baz`
- country: `MX`
- institution: `FES Iztacala`
- department: `PSICOLOGIA`

## Nomenclatura de Cursos Moodle

Los shortnames siguen el patrón: `{asignatura}_{grupo1},{grupo2},{grupo3}`

**Ejemplos:**
- `0202_9282,9283` - Asignatura 0202, grupos 9282 y 9283
- `0616_9614` - Asignatura 0616, grupo 9614
- `1153_9121,9122,9123` - Asignatura 1153, grupos 9121, 9122 y 9123

El script busca el curso que:
1. Empieza con `{asignatura}_`
2. Contiene el grupo del estudiante en la lista de grupos

## Manejo de Errores

El script registra y continúa procesando ante:
- **Usuario ya existe:** Se obtiene su ID y se continúa
- **Curso no encontrado:** Se registra el error y se continúa
- **Ya matriculado:** Se marca como "ya_matriculado"
- **Errores de red:** Se reportan en el reporte final

## Reporte de Salida

El script genera un reporte en la terminal con:

### Resumen
Tabla con conteos de:
- `exito`: Nuevas matriculaciones exitosas
- `usuario_creado`: Usuarios creados + matriculados
- `ya_matriculado`: Estudiantes ya matriculados
- `error_curso_no_encontrado`: Cursos no encontrados
- `error_usuario`: Problemas al crear/obtener usuario
- `error_matriculacion`: Fallos en la matriculación
- `error_conexion`: Errores de conexión a APIs

### Errores Detallados (si existen)
Tabla mostrando:
- Cuenta del estudiante
- Asignatura
- Grupo
- Mensaje de error

Máximo 50 errores mostrados (si hay más, se indica el total)

## Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo `LICENSE` para más detalles.

## Soporte

Para reportar bugs o solicitar features, abre un [issue](https://github.com/tu-usuario/matriculaciones_moodle/issues).

## Cambios recientes

### v0.1.0 (2026-02-02)
- Implementación inicial del script CLI
- Soporte para autenticación con PocketBase v0.23+
- Integración completa con Moodle REST API
- Interfaz visual con Rich (spinners, barras de progreso, tablas)
- Mapeo automático de campos PocketBase → Moodle
- Sistema de caché para cursos de Moodle
- Reporte detallado de errores
