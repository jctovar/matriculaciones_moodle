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
- `batch_get_users()`: Busca múltiples usuarios en una sola llamada
- `batch_check_enrollments()`: Verifica matriculaciones de múltiples usuarios en batch
- `batch_enrol_users()`: Matricula múltiples usuarios simultáneamente
- `_populate_enrollment_cache()`: Precarga cache de matriculaciones para un curso
- `_build_prefix_index()`: Construye índice O(1) para búsqueda de cursos por prefijo

**Optimizaciones:**
- **Cache de matriculaciones**: Evita llamadas repetidas a la API
- **Índice por prefijo**: Búsqueda O(1) de cursos por asignatura
- **Operaciones batch**: Reduce llamadas a la API agrupando operaciones
- **Control de concurrencia**: Semáforo para limitar rate limiting

#### `main.py`
Orquestación del flujo principal y generación de reportes visuales con Rich.

## Mapeo de Campos PocketBase → Moodle

| PocketBase | Moodle | Descripción |
|-----------|--------|-------------|
| cuenta | username, idnumber | Identificador único del usuario |
| nombre | firstname | Nombre |
| apellidos | lastname | Apellidos |
| correo | email | Correo electrónico |
| nacimiento | password | Fecha de nacimiento usada como contraseña (ver nota abajo) |
| asignatura | course shortname | Primera parte del shortname |
| grupo | course shortname | Segunda parte del shortname |

**Nota sobre el campo `nacimiento`:**
- **Formatos aceptados**: ISO 8601 (`1954-08-07 00:00:00.000Z`) o ddmmyyyy (`07081954`)
- El sistema convierte automáticamente de ISO a ddmmyyyy
- Se usa como contraseña inicial en Moodle en formato ddmmyyyy
- Validaciones: día válido (1-31), mes válido (1-12), año válido (1900-2020), fecha válida

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

## Sistema de Logging

El script genera archivos de log detallados para auditoría y debugging:

- **Ubicación**: Raíz del proyecto
- **Formato**: `matriculaciones_{timestamp}.log`
- **Ejemplo**: `matriculaciones_20260205_143022.log`
- **Nivel**: INFO y ERROR
- **Contenido**: Cada operación con timestamp, incluyendo autenticaciones, búsquedas, creaciones y matriculaciones

Los logs persisten después de la ejecución para revisión posterior.

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

## Códigos de Salida

El script retorna los siguientes códigos de salida:

- **0**: Ejecución exitosa sin errores críticos
- **1**: Error crítico que impidió la ejecución (fallo de autenticación, configuración inválida, etc.)

## Testing

El proyecto incluye varios archivos de test para validar funcionalidades específicas:

### Tests Disponibles

1. **`test_conversion_simple.py`**
   - Verifica conversión de formato ISO 8601 a ddmmyyyy
   - Usa datos reales de PocketBase
   ```bash
   python3 test_conversion_simple.py
   ```

2. **`test_formato_iso.py`**
   - Test de conversión y retrocompatibilidad de formatos de fecha
   - Valida que ambos formatos funcionen correctamente
   ```bash
   python3 test_formato_iso.py
   ```

3. **`test_validacion_nacimiento.py`**
   - Verifica todas las validaciones de formato y rangos de fecha
   - Valida día, mes, año y fechas imposibles
   ```bash
   python3 test_validacion_nacimiento.py
   ```

4. **`test_pocketbase_real.py`**
   - Test de integración con PocketBase real
   - Requiere configuración `.env` válida
   ```bash
   python3 test_pocketbase_real.py
   ```

### Ejecutar Todos los Tests

```bash
python3 test_conversion_simple.py && \
python3 test_formato_iso.py && \
python3 test_validacion_nacimiento.py
```

## Requisitos Externos

### Token de Moodle

Para obtener el `MOODLE_TOKEN`:

1. Accede a Moodle como administrador
2. Ve a **Administración del sitio** → **Plugins** → **Servicios web** → **Gestionar tokens**
3. Crea un nuevo token para tu usuario
4. Asegúrate de que el servicio web tenga habilitadas las siguientes funciones:
   - `core_user_get_users_by_field`
   - `core_user_create_users`
   - `core_course_get_courses`
   - `core_enrol_get_enrolled_users`
   - `enrol_manual_enrol_users`

### Permisos en PocketBase

El usuario configurado en `.env` debe tener:

- Acceso de lectura a la vista `reporte_inscripciones`
- Permisos de superadmin o admin (para autenticación en `/_superusers/auth-with-password` o `/api/admins/auth-with-password`)

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
