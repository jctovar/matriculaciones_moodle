# Política de Seguridad

## Reporte de Vulnerabilidades

Si descubres una vulnerabilidad de seguridad, **NO** abras un issue público. En su lugar:

1. **Email:** Contacta a los mantenedores por email privado
2. **Información a incluir:**
   - Descripción de la vulnerabilidad
   - Pasos para reproducir
   - Impacto potencial
   - Sugerencias de mitigación (opcional)

## Información Sensible

### ⚠️ NUNCA Comitees:

- Archivos `.env` (usa `.env.example` para templates)
- Tokens de API o acceso (MOODLE_TOKEN, etc.)
- Credenciales de usuarios/contraseñas
- URLs privadas o internas sin protección
- Documentos `PLAN.md` que contengan ejemplos con credenciales

### Archivos Protegidos por .gitignore:

```
.env                    # Variables de entorno
.env.local
PLAN.md                 # Documentación con tokens/ejemplos
*.log                   # Logs con información sensible
.claude/                # Configuración local de Claude Code
```

## Token de Moodle

El `MOODLE_TOKEN` requiere especial cuidado:

### Si se expone un token:

1. **Inmediato (máx 1 hora):**
   ```
   ✓ Acceder a Moodle como administrador
   ✓ Administración del sitio → Plugins → Servicios web → Gestionar tokens
   ✓ Revocar el token comprometido
   ✓ Generar un nuevo token
   ✓ Actualizar archivo `.env` localmente
   ```

2. **Verificar impacto:**
   ```
   ✓ Revisar logs de acceso a API REST
   ✓ Auditar cambios en usuarios y cursos
   ✓ Verificar si hubo matriculaciones no autorizadas
   ```

3. **Prevención:**
   ```
   ✓ Usar rotación de tokens cada 3-6 meses
   ✓ Limitar permisos del token al mínimo necesario
   ✓ Monitorear uso inusual del token
   ```

### Permisos mínimos requeridos:

El token debe tener SOLO estas funciones de servicio web:
- `core_user_get_users_by_field` - Buscar usuarios
- `core_user_create_users` - Crear nuevos usuarios
- `core_course_get_courses` - Listar cursos
- `core_enrol_get_enrolled_users` - Ver matriculaciones
- `enrol_manual_enrol_users` - Matricular usuarios

**No otorgues permisos adicionales que no sean necesarios.**

## Credenciales de PocketBase

### Buenas prácticas:

1. **Usar cuenta de servicio dedicada:**
   - Crear usuario específico para esta aplicación (no usar admin personal)
   - Limitar permisos a solo lectura en `reporte_inscripciones`

2. **Rotación de contraseña:**
   - Cambiar contraseña cada 3 meses
   - Después de cualquier exposición sospechosa

3. **Monitoreo:**
   - Revisar logs de acceso en PocketBase
   - Alertar si hay intentos fallidos de autenticación

## Pre-commit Hooks

Se recomienda instalar herramientas para detectar secretos:

```bash
# Instalar detect-secrets
pip install detect-secrets

# Crear baseline
detect-secrets scan --baseline .secrets.baseline

# Verificar archivos antes de commit
detect-secrets-hook --baseline .secrets.baseline
```

Agregar a `.git/hooks/pre-commit` para validación automática.

## Escaneo de Secretos en GitHub

Para proyectos con visibilidad pública, GitHub puede escanear automáticamente:

### Habilitar en GitHub:

1. Ir a **Settings** → **Security** → **Secret scanning**
2. Habilitar "Push protection"
3. Agregar patrones personalizados si es necesario

### Responder a alertas:

Si GitHub detecta un secreto:
1. Revocar el secreto inmediatamente
2. Investigar quién/cuándo vio el repositorio
3. Cambiar credenciales afectadas
4. Reescribir historio de git si es necesario

## Auditoría de Seguridad

### Realizar regularmente:

```bash
# Verificar dependencias vulnerables
pip check
pip install safety
safety check

# Escanear archivos por secretos
trufflehog github --org jctovar
detect-secrets audit .secrets.baseline

# Revisar permisos del token en Moodle
# (Desde admin: Administración > Plugins > Servicios web > Gestionar tokens)

# Revisar acceso a PocketBase
# (Desde admin: Settings > Admins/Usuarios > Log de acceso)
```

## Versionamiento Seguro

### Práctica de commits:

1. Nunca hacer commit de archivos `.env`
2. Usar templates (`.env.example`) en su lugar
3. Agregar pre-commit hooks antes de comprometer código
4. Revisar `git diff` antes de cada commit

### Plantilla .env.example:

```env
# Copy to .env and fill with your credentials
API_USERNAME=       # Email de admin/usuario PocketBase
API_PASSWORD=       # Contraseña PocketBase
POCKETBASE_URL=     # URL de PocketBase
MOODLE_URL=         # URL de Moodle
MOODLE_TOKEN=       # Token REST API de Moodle
```

## Contacto de Seguridad

Para vulnerabilidades críticas: [Configurar email de seguridad]

## Agradecimientos

Agradecemos a investigadores de seguridad que reporten vulnerabilidades responsablemente.
