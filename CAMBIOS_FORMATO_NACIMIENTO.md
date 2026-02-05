# Corrección del Formato de Fecha de Nacimiento

## Problema Identificado

La vista `reporte_inscripciones` en PocketBase devuelve el campo `nacimiento` en formato **ISO 8601**:
```
"1954-08-07 00:00:00.000Z"
```

Sin embargo, el código en `models.py` esperaba recibir el formato **ddmmyyyy** (8 dígitos):
```
"07081954"
```

Esto causaba que **todas las inscripciones fallaran** en la validación.

## Solución Implementada

Se modificó el método `Inscripcion.from_pocketbase()` en `src/matriculaciones/models.py` para:

1. **Detectar automáticamente** si el campo viene en formato ISO 8601
2. **Convertir** de ISO a ddmmyyyy cuando sea necesario
3. **Mantener retrocompatibilidad** con el formato ddmmyyyy directo

### Conversión

```python
# Antes (solo aceptaba ddmmyyyy):
nacimiento = "07081954"  # 8 dígitos

# Ahora (acepta ambos formatos):
nacimiento_iso = "1954-08-07 00:00:00.000Z"  # Se convierte a "07081954"
nacimiento_directo = "07081954"              # Se mantiene igual
```

## Validaciones

El código mantiene todas las validaciones originales:

- ✅ Formato debe ser ddmmyyyy (8 dígitos)
- ✅ Día válido (1-31)
- ✅ Mes válido (1-12)
- ✅ Año válido (1900-2020)
- ✅ Fecha válida (sin fechas imposibles como 31 de febrero)

## Uso como Contraseña

El campo `nacimiento` se usa como contraseña en Moodle:

```python
user = {
    "username": "071172664",
    "password": "07081954",  # Formato ddmmyyyy
    ...
}
```

## Tests Ejecutados

### ✅ Test de Conversión ISO
```bash
python3 test_conversion_simple.py
```
- Verifica conversión de formato ISO → ddmmyyyy
- Usa datos reales de PocketBase

### ✅ Test de Validación
```bash
python3 test_validacion_nacimiento.py
```
- Verifica todas las validaciones de formato y rangos
- Mantiene retrocompatibilidad con formato directo

### ✅ Test de Formato ISO Directo
```bash
python3 test_formato_iso.py
```
- Verifica conversión con datos de ejemplo de PocketBase
- Verifica retrocompatibilidad

## Estructura de la Vista PocketBase

La vista `reporte_inscripciones` tiene la siguiente estructura:

```sql
SELECT DISTINCT (ROW_NUMBER() OVER()) as id,
  t2.cuenta, t2.nombre, t2.apellidos, t2.correo, t2.nacimiento,
  t1.asignatura, t1.grupo,
  t1.plan, t1.ciclo, t1.periodo
FROM inscripciones t1
INNER JOIN alumnos t2 ON t1.cuenta = t2.cuenta
WHERE
  t1.plan IN (1164, 1165, 1166, 1167, 1168, 1169, 2256)
  AND t1.tipo = 'O'
ORDER BY t1.cuenta
```

### Campos de la vista:
- `cuenta`: 9 dígitos (pattern: `^[0-9]{9}$`)
- `nombre`: texto requerido
- `apellidos`: texto requerido
- `correo`: email requerido
- **`nacimiento`**: **tipo `date`** (devuelve ISO 8601)
- `asignatura`: 4 dígitos
- `grupo`: formato `[A-Z0-9]{2}[0-9]{2}`
- `plan`: 4 dígitos
- `ciclo`: 1 dígito
- `periodo`: formato `[0-9]{4}[0-2]{1}`

## Compatibilidad

- ✅ Compatible con formato ISO 8601 de PocketBase
- ✅ Mantiene compatibilidad con formato ddmmyyyy directo
- ✅ Todas las validaciones siguen funcionando
- ✅ La contraseña de Moodle usa el formato correcto (ddmmyyyy)

## Archivos Modificados

- `src/matriculaciones/models.py` - Agregada conversión de ISO a ddmmyyyy

## Archivos de Test Creados

- `test_conversion_simple.py` - Test con datos reales de PocketBase
- `test_formato_iso.py` - Test de conversión y retrocompatibilidad
- `test_validacion_nacimiento.py` - Test de validaciones (ya existía)
