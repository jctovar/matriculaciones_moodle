"""Punto de entrada principal del CLI."""

import asyncio
import logging
import sys
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.logging import RichHandler

from .config import Config
from .models import Inscripcion, ResultadoMatriculacion, EstadoMatriculacion
from .pocketbase import PocketBaseClient
from .moodle import MoodleClient, MoodleError

console = Console()


def setup_logging(log_file: str = "matriculaciones.log") -> None:
    """Configura el sistema de logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            RichHandler(console=console, show_time=False, show_path=False, level=logging.WARNING)
        ]
    )


logger = logging.getLogger(__name__)


def _error_result(
    inscripcion: Inscripcion,
    estado: EstadoMatriculacion,
    mensaje: str,
    user_id: int | None = None,
    course_id: int | None = None,
    log_level: str = "error",
) -> ResultadoMatriculacion:
    """Crea un resultado de error con logging consistente."""
    log_msg = f"{inscripcion.cuenta}: {mensaje}"
    if log_level == "warning":
        logger.warning(log_msg)
    else:
        logger.error(log_msg)
    return ResultadoMatriculacion(
        inscripcion=inscripcion,
        estado=estado,
        mensaje=mensaje,
        user_id=user_id,
        course_id=course_id,
    )


async def procesar_batch_optimizado(
    inscripciones: list[Inscripcion],
    moodle: MoodleClient,
) -> list[ResultadoMatriculacion]:
    """Procesa inscripciones con operaciones batch optimizadas."""
    resultados: list[ResultadoMatriculacion] = []
    usuarios_creados: set[str] = set()

    # 1. Pre-cargar usuarios únicos
    usernames = list({i.cuenta for i in inscripciones})
    logger.info(f"Pre-cargando {len(usernames)} usuarios únicos")
    user_cache = await moodle.batch_get_users(usernames)

    # 2. Crear usuarios faltantes
    usuarios_a_crear = [
        i for i in inscripciones
        if user_cache.get(i.cuenta) is None and i.cuenta not in usuarios_creados
    ]
    usuarios_unicos_a_crear = {i.cuenta: i for i in usuarios_a_crear}

    for cuenta, insc in usuarios_unicos_a_crear.items():
        try:
            user = await moodle.create_user(insc)
            user_cache[cuenta] = user
            usuarios_creados.add(cuenta)
        except (MoodleError, ValueError) as e:
            logger.error(f"Error creando usuario {cuenta}: {e}")

    # 3. Resolver cursos y preparar datos
    pendientes: list[tuple[Inscripcion, int, int, str, bool]] = []

    for insc in inscripciones:
        user = user_cache.get(insc.cuenta)
        if not user:
            resultados.append(_error_result(
                insc, EstadoMatriculacion.ERROR_USUARIO, "No se pudo obtener/crear usuario"
            ))
            continue

        user_id = user.get("id")
        if not user_id:
            resultados.append(_error_result(insc, EstadoMatriculacion.ERROR_USUARIO, "Usuario sin ID"))
            continue

        course = await moodle.find_course_for_group(insc.asignatura, insc.grupo)
        if not course:
            resultados.append(_error_result(
                insc,
                EstadoMatriculacion.ERROR_CURSO_NO_ENCONTRADO,
                f"No se encontró curso para {insc.asignatura}_{insc.grupo}",
                user_id=user_id,
                log_level="warning",
            ))
            continue

        course_id = course.get("id")
        if not course_id:
            resultados.append(_error_result(
                insc,
                EstadoMatriculacion.ERROR_CURSO_NO_ENCONTRADO,
                f"Curso sin ID: {course.get('shortname')}",
                user_id=user_id,
            ))
            continue

        pendientes.append((insc, user_id, course_id, course.get("shortname", ""), insc.cuenta in usuarios_creados))

    if not pendientes:
        return resultados

    # 4. Batch check enrollments (A5)
    pairs_to_check = [(user_id, course_id) for _, user_id, course_id, _, _ in pendientes]
    enrollment_status = await moodle.batch_check_enrollments(pairs_to_check)

    # 5. Separar ya matriculados de pendientes
    to_enrol: list[tuple[Inscripcion, int, int, str, bool]] = []
    for insc, user_id, course_id, shortname, was_created in pendientes:
        if enrollment_status.get((user_id, course_id), False):
            resultados.append(ResultadoMatriculacion(
                inscripcion=insc,
                estado=EstadoMatriculacion.YA_MATRICULADO,
                mensaje=f"Ya matriculado en {shortname}",
                user_id=user_id,
                course_id=course_id,
            ))
        else:
            to_enrol.append((insc, user_id, course_id, shortname, was_created))

    if not to_enrol:
        return resultados

    # 6. Batch enroll (A1)
    enrol_pairs = [(user_id, course_id) for _, user_id, course_id, _, _ in to_enrol]
    enrol_results = await moodle.batch_enrol_users(enrol_pairs)

    for insc, user_id, course_id, shortname, was_created in to_enrol:
        success = enrol_results.get((user_id, course_id), False)
        if success:
            estado = EstadoMatriculacion.USUARIO_CREADO if was_created else EstadoMatriculacion.EXITO
            logger.info(f"Matriculación exitosa: {insc.cuenta} en {shortname}")
            resultados.append(ResultadoMatriculacion(
                inscripcion=insc,
                estado=estado,
                mensaje=f"Matriculado en {shortname}",
                user_id=user_id,
                course_id=course_id,
            ))
        else:
            resultados.append(_error_result(
                insc,
                EstadoMatriculacion.ERROR_MATRICULACION,
                f"Error en batch enrol para {shortname}",
                user_id=user_id,
                course_id=course_id,
            ))

    return resultados


def mostrar_reporte(resultados: list[ResultadoMatriculacion]) -> None:
    """Muestra el reporte final de matriculaciones."""
    # Contadores
    contadores = {estado: 0 for estado in EstadoMatriculacion}
    for r in resultados:
        contadores[r.estado] += 1

    # Tabla de resumen
    console.print("\n[bold]Resumen de Matriculaciones[/bold]\n")

    resumen = Table(show_header=True, header_style="bold cyan")
    resumen.add_column("Estado", style="dim")
    resumen.add_column("Cantidad", justify="right")

    estado_colores = {
        EstadoMatriculacion.EXITO: "green",
        EstadoMatriculacion.USUARIO_CREADO: "green",
        EstadoMatriculacion.YA_MATRICULADO: "yellow",
        EstadoMatriculacion.ERROR_CURSO_NO_ENCONTRADO: "red",
        EstadoMatriculacion.ERROR_USUARIO: "red",
        EstadoMatriculacion.ERROR_MATRICULACION: "red",
        EstadoMatriculacion.ERROR_CONEXION: "red",
    }

    for estado, cantidad in contadores.items():
        if cantidad > 0:
            color = estado_colores.get(estado, "white")
            resumen.add_row(
                f"[{color}]{estado.value}[/{color}]",
                str(cantidad),
            )

    console.print(resumen)

    # Mostrar errores detallados
    errores = [
        r
        for r in resultados
        if r.estado
        in [
            EstadoMatriculacion.ERROR_CURSO_NO_ENCONTRADO,
            EstadoMatriculacion.ERROR_USUARIO,
            EstadoMatriculacion.ERROR_MATRICULACION,
            EstadoMatriculacion.ERROR_CONEXION,
        ]
    ]

    if errores:
        console.print("\n[bold red]Errores Detallados[/bold red]\n")
        errores_table = Table(show_header=True, header_style="bold red")
        errores_table.add_column("Cuenta")
        errores_table.add_column("Asignatura")
        errores_table.add_column("Grupo")
        errores_table.add_column("Error")

        for r in errores[:50]:
            errores_table.add_row(
                r.inscripcion.cuenta,
                r.inscripcion.asignatura,
                r.inscripcion.grupo,
                r.mensaje[:60],
            )

        if len(errores) > 50:
            console.print(f"(Mostrando 50 de {len(errores)} errores)")

        console.print(errores_table)


async def run() -> int:
    """Ejecuta el proceso principal de matriculación."""
    # Configurar logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"matriculaciones_{timestamp}.log"
    setup_logging(log_file)

    console.print("[bold blue]Matriculaciones Moodle[/bold blue]\n")
    logger.info("="*80)
    logger.info("Iniciando proceso de matriculaciones")
    logger.info(f"Archivo de log: {log_file}")
    logger.info("="*80)

    # 1. Cargar configuración
    try:
        config = Config.from_env()
        logger.info("Configuración cargada exitosamente")
    except ValueError as e:
        logger.error(f"Error de configuración: {e}")
        console.print(f"[red]Error de configuración:[/red] {e}")
        return 1

    # 2. Conectar a PocketBase
    pb = PocketBaseClient(config.pocketbase_url)

    with console.status("[bold green]Conectando a PocketBase..."):
        try:
            await pb.authenticate(config.api_username, config.api_password)
            console.print("[green]✓[/green] Conectado a PocketBase")
            logger.info("Conexión a PocketBase exitosa")
        except Exception as e:
            logger.error(f"Error al conectar a PocketBase: {e}", exc_info=True)
            console.print(f"[red]Error al conectar a PocketBase:[/red] {e}")
            return 1

    # 3. Descargar inscripciones
    with console.status("[bold green]Descargando inscripciones..."):
        try:
            inscripciones = await pb.get_inscripciones()
            console.print(
                f"[green]✓[/green] {len(inscripciones)} inscripciones descargadas"
            )
            logger.info(f"Descargadas {len(inscripciones)} inscripciones")
        except Exception as e:
            logger.error(f"Error al descargar inscripciones: {e}", exc_info=True)
            console.print(f"[red]Error al descargar inscripciones:[/red] {e}")
            return 1

    if not inscripciones:
        logger.info("No hay inscripciones para procesar")
        console.print("[yellow]No hay inscripciones para procesar[/yellow]")
        return 0

    # 4. Procesar inscripciones
    max_concurrent = 10
    moodle = MoodleClient(config.moodle_url, config.moodle_token, max_concurrent=max_concurrent)

    # Precargar cursos para evitar llamadas repetidas
    with console.status("[bold green]Cargando cursos de Moodle..."):
        try:
            courses = await moodle.get_all_courses()
            console.print(f"[green]✓[/green] {len(courses)} cursos cargados")
            logger.info(f"Cargados {len(courses)} cursos de Moodle")
        except Exception as e:
            logger.error(f"Error al cargar cursos: {e}", exc_info=True)
            console.print(f"[red]Error al cargar cursos:[/red] {e}")
            return 1

    logger.info(f"Iniciando procesamiento de {len(inscripciones)} inscripciones")
    logger.info(f"Concurrencia máxima: {max_concurrent}")

    with console.status("[bold green]Procesando matriculaciones (batch optimizado)..."):
        resultados = await procesar_batch_optimizado(inscripciones, moodle)

    logger.info("Procesamiento completado")

    # 5. Mostrar reporte
    mostrar_reporte(resultados)

    # Código de salida según errores
    errores_count = sum(
        1
        for r in resultados
        if r.estado
        in [
            EstadoMatriculacion.ERROR_USUARIO,
            EstadoMatriculacion.ERROR_MATRICULACION,
            EstadoMatriculacion.ERROR_CONEXION,
        ]
    )

    # Logging de resumen
    exitosos = sum(1 for r in resultados if r.estado in [EstadoMatriculacion.EXITO, EstadoMatriculacion.USUARIO_CREADO])
    ya_matriculados = sum(1 for r in resultados if r.estado == EstadoMatriculacion.YA_MATRICULADO)

    logger.info("="*80)
    logger.info("RESUMEN FINAL:")
    logger.info(f"  Total procesados: {len(resultados)}")
    logger.info(f"  Exitosos: {exitosos}")
    logger.info(f"  Ya matriculados: {ya_matriculados}")
    logger.info(f"  Errores: {errores_count}")
    logger.info(f"  Código de salida: {1 if errores_count > 0 else 0}")
    logger.info(f"  Log guardado en: {log_file}")
    logger.info("="*80)

    return 1 if errores_count > 0 else 0


def main() -> None:
    """Punto de entrada del CLI."""
    sys.exit(asyncio.run(run()))


if __name__ == "__main__":
    main()
