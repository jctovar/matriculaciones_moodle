"""Punto de entrada principal del CLI."""

import asyncio
import sys

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from .config import Config
from .models import Inscripcion, ResultadoMatriculacion, EstadoMatriculacion
from .pocketbase import PocketBaseClient
from .moodle import MoodleClient, MoodleError

console = Console()


async def procesar_inscripcion(
    inscripcion: Inscripcion,
    moodle: MoodleClient,
) -> ResultadoMatriculacion:
    """Procesa una inscripción individual."""
    try:
        # 1. Buscar o crear usuario
        user = await moodle.get_user_by_username(inscripcion.cuenta)
        usuario_creado = False

        if not user:
            try:
                user = await moodle.create_user(inscripcion)
                usuario_creado = True
            except MoodleError as e:
                if "username already exists" in str(e).lower():
                    user = await moodle.get_user_by_username(inscripcion.cuenta)
                else:
                    return ResultadoMatriculacion(
                        inscripcion=inscripcion,
                        estado=EstadoMatriculacion.ERROR_USUARIO,
                        mensaje=str(e),
                    )

        if not user:
            return ResultadoMatriculacion(
                inscripcion=inscripcion,
                estado=EstadoMatriculacion.ERROR_USUARIO,
                mensaje="No se pudo obtener o crear el usuario",
            )

        user_id = user.get("id")

        # 2. Buscar curso
        course = await moodle.find_course_for_group(
            inscripcion.asignatura, inscripcion.grupo
        )

        if not course:
            return ResultadoMatriculacion(
                inscripcion=inscripcion,
                estado=EstadoMatriculacion.ERROR_CURSO_NO_ENCONTRADO,
                mensaje=f"No se encontró curso para {inscripcion.asignatura}_{inscripcion.grupo}",
                user_id=user_id,
            )

        course_id = course.get("id")

        # 3. Verificar si ya está matriculado
        if await moodle.is_user_enrolled(user_id, course_id):
            return ResultadoMatriculacion(
                inscripcion=inscripcion,
                estado=EstadoMatriculacion.YA_MATRICULADO,
                mensaje=f"Ya matriculado en {course.get('shortname')}",
                user_id=user_id,
                course_id=course_id,
            )

        # 4. Matricular
        await moodle.enrol_user(user_id, course_id)

        estado = (
            EstadoMatriculacion.USUARIO_CREADO
            if usuario_creado
            else EstadoMatriculacion.EXITO
        )

        return ResultadoMatriculacion(
            inscripcion=inscripcion,
            estado=estado,
            mensaje=f"Matriculado en {course.get('shortname')}",
            user_id=user_id,
            course_id=course_id,
        )

    except MoodleError as e:
        return ResultadoMatriculacion(
            inscripcion=inscripcion,
            estado=EstadoMatriculacion.ERROR_MATRICULACION,
            mensaje=str(e),
        )
    except Exception as e:
        return ResultadoMatriculacion(
            inscripcion=inscripcion,
            estado=EstadoMatriculacion.ERROR_CONEXION,
            mensaje=str(e),
        )


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
    console.print("[bold blue]Matriculaciones Moodle[/bold blue]\n")

    # 1. Cargar configuración
    try:
        config = Config.from_env()
    except ValueError as e:
        console.print(f"[red]Error de configuración:[/red] {e}")
        return 1

    # 2. Conectar a PocketBase
    pb = PocketBaseClient(config.pocketbase_url)

    with console.status("[bold green]Conectando a PocketBase..."):
        try:
            await pb.authenticate(config.api_username, config.api_password)
            console.print("[green]✓[/green] Conectado a PocketBase")
        except Exception as e:
            console.print(f"[red]Error al conectar a PocketBase:[/red] {e}")
            return 1

    # 3. Descargar inscripciones
    with console.status("[bold green]Descargando inscripciones..."):
        try:
            inscripciones = await pb.get_inscripciones()
            console.print(
                f"[green]✓[/green] {len(inscripciones)} inscripciones descargadas"
            )
        except Exception as e:
            console.print(f"[red]Error al descargar inscripciones:[/red] {e}")
            return 1

    if not inscripciones:
        console.print("[yellow]No hay inscripciones para procesar[/yellow]")
        return 0

    # 4. Procesar inscripciones
    moodle = MoodleClient(config.moodle_url, config.moodle_token)
    resultados: list[ResultadoMatriculacion] = []

    # Precargar cursos para evitar llamadas repetidas
    with console.status("[bold green]Cargando cursos de Moodle..."):
        try:
            courses = await moodle.get_all_courses()
            console.print(f"[green]✓[/green] {len(courses)} cursos cargados")
        except Exception as e:
            console.print(f"[red]Error al cargar cursos:[/red] {e}")
            return 1

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            "[cyan]Procesando matriculaciones...", total=len(inscripciones)
        )

        for inscripcion in inscripciones:
            resultado = await procesar_inscripcion(inscripcion, moodle)
            resultados.append(resultado)
            progress.update(task, advance=1)

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

    return 1 if errores_count > 0 else 0


def main() -> None:
    """Punto de entrada del CLI."""
    sys.exit(asyncio.run(run()))


if __name__ == "__main__":
    main()
