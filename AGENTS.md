# AGENTS.md

## Proyecto
Agenda AI es una app Python con Streamlit + SQLAlchemy + SQLite.
La arquitectura base es:
- `app/services/`
- `app/repositories/`
- `app/db/models/`
- `app/ui/`

## Reglas de trabajo
- No crear una arquitectura paralela.
- Reutilizar servicios, repositorios y modelos existentes antes de agregar lógica nueva.
- No agregar dependencias nuevas salvo que se pida explícitamente.
- No inventar campos o tablas que no existan.
- Mantener cambios mínimos, idiomáticos y consistentes con el repo.
- Antes de editar, inspeccionar los archivos relacionados al flujo afectado.
- Si una tarea depende de referencias conversacionales, reutilizar `app/services/reference_resolver.py`.
- Si una tarea afecta UI, revisar `app/ui/conversation_page.py`.
- Si una tarea afecta persistencia, revisar primero `repositories/` y después `db/models/`.

## Flujo esperado para cambios
1. Inspeccionar archivos relevantes.
2. Proponer o aplicar cambios mínimos.
3. Ejecutar validación.
4. Dejar resumen técnico y pruebas manuales.

## Validación obligatoria
Después de cambios en Python:
- correr `scripts/validate.ps1`

Si el cambio toca parser, resolver o response service:
- además indicar pruebas manuales concretas para la UI del asistente.

## Formato de salida esperado
Al terminar cualquier tarea, devolver:

1. RESUMEN EJECUTIVO
- qué implementaste
- qué no implementaste
- limitaciones reales

2. ARCHIVOS MODIFICADOS
Para cada archivo:
- ruta
- por qué lo tocaste
- resumen del cambio

3. DETALLE TÉCNICO
- flujo final
- decisiones importantes
- cómo se evita romper comportamiento existente

4. DIF O CÓDIGO FINAL
- diff o contenido final relevante

5. PRUEBAS MANUALES
- inputs concretos
- comportamiento esperado

6. RIESGOS / COSAS A REVISAR
- edge cases
- deuda técnica
- limitaciones

7. BLOQUE PARA CHATGPT
Debe empezar exactamente con:
=== PARA CHATGPT ===

Y terminar exactamente con:
=== FIN PARA CHATGPT ===

## Notas para entorno Windows
- Preferir PowerShell.
- No asumir WSL.
- No asumir que existe un `.venv` activo: verificar primero.
- Si hace falta instalar dependencias, usar el script de setup del repo.

## Comandos útiles
Setup:
- `powershell -ExecutionPolicy Bypass -File scripts/setup_codex.ps1`

Validación:
- `powershell -ExecutionPolicy Bypass -File scripts/validate.ps1`
