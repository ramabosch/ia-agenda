$OutputPath = Join-Path $PSScriptRoot "repo_summary.pdf"

$Title = "Resumen del Repo: Agenda AI"

$Lines = @(
    "Proyecto Python con Streamlit + SQLAlchemy + SQLite para gestionar una agenda operativa de clientes, proyectos y tareas, con un asistente en lenguaje natural para consultar o actualizar la agenda.",
    "",
    "Flujo general",
    "UI Streamlit -> services -> repositories -> models SQLAlchemy -> SQLite",
    "Asistente -> parser hibrido (LLM local o reglas) -> intent -> accion o consulta -> log conversacional",
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
    "app/services/task_service.py: wrappers de tareas, cambios de estado, prioridad, contexto y resumen operativo por tarea.",
    "app/services/task_update_service.py: wrappers de updates.",
    "app/services/conversation_service.py: guardar y consultar conversaciones.",
    "app/services/text_normalizer_service.py: normalizacion simple de texto para busquedas por nombre.",
    "app/services/query_parser_service.py: parser por reglas y regex para consultas en espanol.",
    "app/services/llm_parser_service.py: parser via modelo local compatible con chat completions; pide JSON estricto.",
    "app/services/hybrid_parser_service.py: primero intenta LLM y luego hace fallback a reglas.",
    "app/services/query_response_service.py: dispatcher principal del asistente; resuelve intents y ejecuta consultas o cambios.",
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
    "task_repository.py tiene search_tasks_by_name duplicada."
)

function Escape-PdfText {
    param([string]$Text)
    return $Text.Replace('\', '\\').Replace('(', '\(').Replace(')', '\)')
}

function Wrap-Text {
    param(
        [string]$Text,
        [int]$MaxChars = 90
    )

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return @("")
    }

    $words = $Text -split '\s+'
    $result = New-Object System.Collections.Generic.List[string]
    $current = $words[0]

    for ($i = 1; $i -lt $words.Length; $i++) {
        $candidate = "$current $($words[$i])"
        if ($candidate.Length -le $MaxChars) {
            $current = $candidate
        }
        else {
            $result.Add($current)
            $current = $words[$i]
        }
    }

    $result.Add($current)
    return $result
}

$allLines = @($Title, "") + $Lines
$pages = New-Object System.Collections.Generic.List[object]
$currentPage = New-Object System.Collections.Generic.List[string]
$y = 800
$leading = 14

foreach ($rawLine in $allLines) {
    $wrappedLines = Wrap-Text -Text $rawLine -MaxChars 90
    foreach ($line in $wrappedLines) {
        if ($y -lt 60) {
            $pages.Add($currentPage)
            $currentPage = New-Object System.Collections.Generic.List[string]
            $y = 800
        }

        $currentPage.Add($line)
        $y -= $leading
    }
}

if ($currentPage.Count -gt 0) {
    $pages.Add($currentPage)
}

$objects = New-Object System.Collections.Generic.List[string]
$pageObjectIds = New-Object System.Collections.Generic.List[int]
$contentObjectIds = New-Object System.Collections.Generic.List[int]
$nextId = 3

foreach ($page in $pages) {
    $commands = New-Object System.Collections.Generic.List[string]
    $commands.Add("BT")
    $commands.Add("/F1 11 Tf")
    $commands.Add("50 810 Td")
    $commands.Add("14 TL")

    $first = $true
    foreach ($line in $page) {
        $safe = Escape-PdfText $line
        if ($first) {
            $commands.Add("($safe) Tj")
            $first = $false
        }
        else {
            $commands.Add("T* ($safe) Tj")
        }
    }
    $commands.Add("ET")

    $stream = [string]::Join("`n", $commands)
    $contentObjectIds.Add($nextId)
    $objects.Add("$nextId 0 obj`n<< /Length $($stream.Length) >>`nstream`n$stream`nendstream`nendobj`n")
    $nextId++

    $pageObjectIds.Add($nextId)
    $objects.Add("$nextId 0 obj`n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 1 0 R >> >> /Contents $($contentObjectIds[$contentObjectIds.Count - 1]) 0 R >>`nendobj`n")
    $nextId++
}

$catalogId = $nextId
$pageRefs = [string]::Join(" ", ($pageObjectIds | ForEach-Object { "$_ 0 R" }))
$pagesObject = "2 0 obj`n<< /Type /Pages /Count $($pageObjectIds.Count) /Kids [$pageRefs] >>`nendobj`n"

$finalObjects = New-Object System.Collections.Generic.List[string]
$finalObjects.Add("1 0 obj`n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>`nendobj`n")
$finalObjects.Add($pagesObject)
foreach ($obj in $objects) {
    $finalObjects.Add($obj)
}
$finalObjects.Add("$catalogId 0 obj`n<< /Type /Catalog /Pages 2 0 R >>`nendobj`n")

$builder = New-Object System.Text.StringBuilder
[void]$builder.Append("%PDF-1.4`n")

$offsets = New-Object System.Collections.Generic.List[int]
$offsets.Add(0)

foreach ($obj in $finalObjects) {
    $offsets.Add($builder.Length)
    [void]$builder.Append($obj)
}

$xrefStart = $builder.Length
[void]$builder.Append("xref`n0 $($offsets.Count)`n")
[void]$builder.Append("0000000000 65535 f `n")

for ($i = 1; $i -lt $offsets.Count; $i++) {
    [void]$builder.Append(("{0:D10} 00000 n `n" -f $offsets[$i]))
}

[void]$builder.Append("trailer`n<< /Size $($offsets.Count) /Root $catalogId 0 R >>`n")
[void]$builder.Append("startxref`n$xrefStart`n%%EOF`n")

[System.IO.File]::WriteAllBytes($OutputPath, [System.Text.Encoding]::ASCII.GetBytes($builder.ToString()))
Write-Output $OutputPath
