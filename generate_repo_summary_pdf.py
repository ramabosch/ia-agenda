from pathlib import Path


OUTPUT_PATH = Path("repo_summary.pdf")

TITLE = "Resumen del Repo: Agenda AI"

LINES = [
    "Proyecto Python con Streamlit + SQLAlchemy + SQLite para gestionar una agenda operativa de clientes, proyectos y tareas, con un asistente en lenguaje natural para consultar o actualizar la agenda.",
    "",
    "Flujo general",
    "UI Streamlit -> services -> repositories -> models SQLAlchemy -> SQLite",
    "Asistente -> parser hibrido (LLM local o reglas) -> intent -> accion/consulta -> log conversacional",
    "",
    "Estructura principal",
    "run.py: entry point real. Inicializa la DB, configura Streamlit y expone la navegacion entre paginas.",
    "requirements.txt: dependencias del proyecto. Lo central es streamlit, sqlalchemy, requests y pandas.",
    "data/agenda.db: base SQLite local con clientes, proyectos, tareas, updates y logs del asistente.",
    "app/config.py: configuracion global de DB y del parser LLM local.",
    "app/main.py: vacio actualmente.",
    "",
    "Capa de datos",
    "app/db/base.py: base declarativa de SQLAlchemy.",
    "app/db/session.py: engine y SessionLocal.",
    "app/db/__init__.py: init_db() para crear tablas.",
    "app/db/models/client.py: modelo Client; nombre, empresa, notas y relacion con proyectos.",
    "app/db/models/project.py: modelo Project; pertenece a un cliente y contiene tareas.",
    "app/db/models/task.py: modelo Task; titulo, descripcion, estado, prioridad, vencimiento, contexto y timestamps.",
    "app/db/models/task_update.py: historial de updates por tarea.",
    "app/db/models/conversation_log.py: registro de conversaciones del asistente.",
    "",
    "Enums y schemas",
    "app/schemas/enums.py: estados de proyecto, estados de tarea y prioridades.",
    "app/schemas/README.md: vacio.",
    "",
    "Repositories",
    "app/repositories/client_repository.py: alta, listado y busqueda de clientes.",
    "app/repositories/project_repository.py: alta, listados y busquedas de proyectos.",
    "app/repositories/task_repository.py: alta, filtros y actualizaciones de tareas.",
    "app/repositories/task_update_repository.py: alta y lectura de historial de updates.",
    "app/repositories/conversation_repository.py: persistencia y consulta de logs conversacionales.",
    "",
    "Services",
    "app/services/client_service.py: wrappers de clientes con manejo de sesion DB.",
    "app/services/project_service.py: wrappers de proyectos y resumen operativo por proyecto.",
    "app/services/task_service.py: wrappers de tareas, cambios de estado/prioridad/contexto y resumen operativo por tarea.",
    "app/services/task_update_service.py: wrappers de updates.",
    "app/services/conversation_service.py: guardar y consultar conversaciones.",
    "app/services/text_normalizer_service.py: normalizacion simple de texto para busquedas por nombre.",
    "app/services/query_parser_service.py: parser por reglas/regex para consultas en espanol.",
    "app/services/llm_parser_service.py: parser via modelo local compatible con chat completions; pide JSON estricto.",
    "app/services/hybrid_parser_service.py: primero intenta LLM y luego hace fallback a reglas.",
    "app/services/query_response_service.py: dispatcher principal del asistente; resuelve intents y ejecuta consultas/cambios.",
    "app/services/reference_resolver.py: vacio actualmente.",
    "",
    "UI",
    "app/ui/dashboard.py: metricas y listas de tareas vencidas, de hoy, en progreso y bloqueadas.",
    "app/ui/clients_page.py: crear y listar clientes.",
    "app/ui/projects_page.py: crear, filtrar y listar proyectos.",
    "app/ui/tasks_page.py: crear, filtrar, editar tareas, actualizar contexto y ver historial.",
    "app/ui/ai_queries_page.py: pantalla auxiliar con vistas estructuradas para IA.",
    "app/ui/conversation_page.py: interfaz del asistente conversacional.",
    "",
    "Modelo conceptual",
    "Cliente -> Proyecto -> Tarea -> TaskUpdate",
    "El asistente tambien guarda ConversationLog con input, interpretacion y respuesta.",
    "",
    "Decisiones actuales de arquitectura",
    "SQLite local, sin migraciones.",
    "No hay API REST; todo corre dentro de Streamlit.",
    "Services delgados y repositories funcionales.",
    "Parser hibrido: LLM local opcional mas fallback regex.",
    "",
    "Observaciones utiles",
    "app/main.py y app/services/reference_resolver.py estan vacios.",
    "conversation_page.py genera la respuesta del asistente y la guarda, pero no la muestra claramente en pantalla.",
    "task_service.py referencia search_tasks_by_name_and_client_id, pero no aparece implementado en task_repository.py.",
    "task_repository.py tiene search_tasks_by_name duplicada.",
]


def escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def wrap_text(text: str, max_chars: int = 92) -> list[str]:
    if not text:
        return [""]

    words = text.split()
    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]

    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            lines.append(current)
            current = word

    lines.append(current)
    return lines


def build_content_stream() -> bytes:
    y = 800
    leading = 14
    page_index = 1
    page_count = 1
    page_lines: list[list[str]] = [[]]

    all_lines = [TITLE, ""] + LINES

    for raw_line in all_lines:
        wrapped = wrap_text(raw_line, max_chars=90)
        for line in wrapped:
            if y < 60:
                page_lines.append([])
                page_count += 1
                y = 800
            page_lines[-1].append(line)
            y -= leading

    objects: list[bytes] = []
    page_object_ids: list[int] = []
    content_object_ids: list[int] = []

    obj_id = 3
    for lines in page_lines:
        content_commands = ["BT", "/F1 11 Tf", "50 810 Td", "14 TL"]
        first = True
        for line in lines:
            safe = escape_pdf_text(line)
            if first:
                content_commands.append(f"({safe}) Tj")
                first = False
            else:
                content_commands.append(f"T* ({safe}) Tj")
        content_commands.append("ET")
        content_data = "\n".join(content_commands).encode("latin-1", errors="replace")
        content_object_ids.append(obj_id)
        objects.append(
            f"{obj_id} 0 obj\n<< /Length {len(content_data)} >>\nstream\n".encode("latin-1")
            + content_data
            + b"\nendstream\nendobj\n"
        )
        obj_id += 1

        page_object_ids.append(obj_id)
        objects.append(
            (
                f"{obj_id} 0 obj\n"
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                f"/Resources << /Font << /F1 1 0 R >> >> /Contents {content_object_ids[-1]} 0 R >>\n"
                f"endobj\n"
            ).encode("latin-1")
        )
        obj_id += 1

    kids = " ".join(f"{pid} 0 R" for pid in page_object_ids)
    pages_obj = (
        f"2 0 obj\n<< /Type /Pages /Count {len(page_object_ids)} /Kids [{kids}] >>\nendobj\n"
    ).encode("latin-1")
    catalog_obj = b"3_placeholder"
    trailer_objects: list[bytes] = [
        b"1 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        pages_obj,
    ]

    catalog_id = obj_id
    trailer_objects.extend(objects)
    trailer_objects.append(
        f"{catalog_id} 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n".encode("latin-1")
    )

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in trailer_objects:
        offsets.append(len(pdf))
        pdf.extend(obj)

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))

    pdf.extend(
        (
            f"trailer\n<< /Size {len(offsets)} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode("latin-1")
    )
    return bytes(pdf)


def main() -> None:
    OUTPUT_PATH.write_bytes(build_content_stream())
    print(OUTPUT_PATH.resolve())


if __name__ == "__main__":
    main()
