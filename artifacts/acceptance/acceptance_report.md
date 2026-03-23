# Acceptance Suite Report

- Generated at: 2026-03-23T00:34:57.878617
- Scenarios: 7
- PASS: 7
- FAIL: 0
- PARTIAL: 0
- Gate status: APTO
- By category: {'friction': {'pass': 1, 'fail': 0, 'partial': 0, 'total': 1}, 'recommendation': {'pass': 1, 'fail': 0, 'partial': 0, 'total': 1}, 'clarification': {'pass': 1, 'fail': 0, 'partial': 0, 'total': 1}, 'compound': {'pass': 1, 'fail': 0, 'partial': 0, 'total': 1}, 'continuity': {'pass': 1, 'fail': 0, 'partial': 0, 'total': 1}, 'temporal': {'pass': 1, 'fail': 0, 'partial': 0, 'total': 1}, 'safety': {'pass': 1, 'fail': 0, 'partial': 0, 'total': 1}}
- By severity: {'critical': {'pass': 5, 'fail': 0, 'partial': 0, 'total': 5}, 'high': {'pass': 1, 'fail': 0, 'partial': 0, 'total': 1}, 'medium': {'pass': 1, 'fail': 0, 'partial': 0, 'total': 1}}
- Filters: {'categories': [], 'severities': [], 'tags': ['smoke_critical']}

## FRI-001 - Friccion global por atraso

- Category: friction
- Severity: critical
- Tags: daily, friction, regression, smoke_critical
- Status: PASS
- Turns: 1
- Expected checks: should_have_intent, should_have_action_status, should_contain_any
- Human review note: n/a

### Turn 1

- Input: `que esta frenado hace mucho`
- Intent: `get_operational_friction_summary`
- Scope: `global`
- Action status: `informational`
- Clarification: `False`
- Degraded: `False`
- Context reused: `False`
- Mutations: `0`

Output:

```text
Lo que hoy muestra mas estancamiento o friccion es:
Estado general: Hay 8 tareas abiertas. 5 muestran friccion operativa. 4 tienen senales mas fuertes de estancamiento.
Tareas destacadas por friccion:
- Resolver integracion CRM | Proyecto: Automatizacion | Cliente: Cam | Senales: bloqueada hace tiempo, abierta hace bastante sin cierre, alta prioridad sin proxima accion
- Revisar indicadores | Proyecto: Dashboard comercial | Cliente: Cam | Senales: bloqueada hace tiempo, abierta hace bastante sin cierre, alta prioridad sin proxima accion
- Actualizar indicadores de ventas | Proyecto: Dashboard ventas | Cliente: Cam | Senales: en progreso hace demasiado, abierta hace bastante sin cierre, alta prioridad sin proxima accion
- Definir metricas | Proyecto: Dashboard comercial | Cliente: Cam | Senales: abierta hace bastante sin cierre, alta prioridad sin proxima accion
- Revisar proveedores | Proyecto: Ops interno | Cliente: Lumen | Senales: sin proxima accion clara
Proyectos con mas friccion:
- Dashboard comercial (Cam) | Friccion: 2 | Bloqueadas: 1 | Sin next_action: 2
- Automatizacion (Cam) | Friccion: 1 | Bloqueadas: 1 | Sin next_action: 1
- Dashboard ventas (Cam) | Friccion: 1 | Bloqueadas: 0 | Sin next_action: 1
Clientes que merecen atencion:
- Cam | Friccion: 4 | Senales fuertes: 4
- Lumen | Friccion: 1 | Senales fuertes: 0
Recomendacion: Primero destrabaria 'Resolver integracion CRM', porque combina bloqueo y senal temporal de atraso.
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_response: PASS (hay respuesta)
- should_have_audit_trace: PASS (audit trace presente)
- should_have_intent: PASS (intent=get_operational_friction_summary)
- should_have_action_status: PASS (action_status=informational)
- should_contain_any: PASS (matches=['friccion', 'estancamiento'])

## REC-003 - Que haria ahora con un cliente

- Category: recommendation
- Severity: critical
- Tags: daily, client, recommendation, smoke_critical
- Status: PASS
- Turns: 1
- Expected checks: n/a
- Human review note: n/a

### Turn 1

- Input: `que harias ahora con Cam`
- Intent: `get_operational_recommendation`
- Scope: `client`
- Action status: `informational`
- Clarification: `False`
- Degraded: `False`
- Context reused: `False`
- Mutations: `0`

Output:

```text
Lo que yo haria con Cam:
Estado general: Hay 4 proyectos y 7 tareas abiertas. Priorice donde veo mas impacto con este cliente.
Recomendaciones concretas:
- Primero: Resolver integracion CRM | Proyecto: Automatizacion | Cliente: Cam | Porque: esta bloqueada hace tiempo, es de alta prioridad y no tiene proxima accion, lleva bastante abierta, le falta seguimiento concreto | Recomendacion conservadora: definir proxima accion
- Como segunda opcion: Revisar indicadores | Proyecto: Dashboard comercial | Cliente: Cam | Porque: esta bloqueada hace tiempo, es de alta prioridad y no tiene proxima accion, lleva bastante abierta, le falta seguimiento concreto | Recomendacion conservadora: definir proxima accion
- Como tercera opcion: Actualizar indicadores de ventas | Proyecto: Dashboard ventas | Cliente: Cam | Porque: es de alta prioridad y no tiene proxima accion, lleva demasiado en progreso, le falta seguimiento concreto | Recomendacion conservadora: definir proxima accion
Recomendacion principal: Si tuviera que elegir una sola cosa, iria primero por 'Resolver integracion CRM'.
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_response: PASS (hay respuesta)
- should_have_scope: PASS (scope=client)
- should_have_intent: PASS (intent=get_operational_recommendation)
- should_contain_any: PASS (matches=['lo que yo haria con cam', 'recomendacion principal'])

## CLR-001 - Continuacion de clarificacion para creacion

- Category: clarification
- Severity: critical
- Tags: daily, clarification, multi_turn, safe_write, smoke_critical
- Status: PASS
- Turns: 2
- Expected checks: should_clarify, should_have_context_reuse
- Human review note: Reclasificado: la clarificacion de create expone opciones confiables en el texto, pero no garantiza una lista estructurada completa de candidatos para este flujo.

### Turn 1

- Input: `agregame una tarea a Cam: definir metricas`
- Intent: `create_task`
- Scope: `client`
- Action status: `degraded`
- Clarification: `False`
- Degraded: `True`
- Context reused: `False`
- Mutations: `0`

Output:

```text
El cliente 'Cam' tiene varios proyectos. Decime en cual queres crearlo. Opciones: Dashboard comercial, Dashboard ventas, Automatizacion.
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_clarify: PASS (clarificacion detectada)
- should_not_mutate: PASS (mutaciones=0)
- should_contain_any: PASS (matches=['dashboard comercial', 'dashboard ventas', 'automatizacion'])

### Turn 2

- Input: `en dashboard comercial`
- Intent: `clarify_entity_reference`
- Scope: `project`
- Action status: `None`
- Clarification: `False`
- Degraded: `False`
- Context reused: `True`
- Mutations: `0`

Output:

```text
Resumen del proyecto Dashboard comercial:
Cliente: Cam
Estado: activo
Descripcion: Seguimiento comercial
Tareas totales: 3
Tareas abiertas: 3
En progreso: 0
Bloqueadas: 1
Hechas: 0
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_response: PASS (hay respuesta)
- should_have_scope: PASS (scope=project)
- should_have_context_reuse: PASS (reuso de contexto/snapshot)
- should_not_mutate: PASS (mutaciones=0)
- should_contain_any: PASS (matches=['resumen del proyecto dashboard comercial', 'cliente: cam'])

## CMP-001 - Compuesto resumen mas recomendacion

- Category: compound
- Severity: critical
- Tags: daily, compound, client, smoke_critical
- Status: PASS
- Turns: 1
- Expected checks: n/a
- Human review note: n/a

### Turn 1

- Input: `resumime Cam y decime que harias primero`
- Intent: `compound_query`
- Scope: `client`
- Action status: `informational`
- Clarification: `False`
- Degraded: `False`
- Context reused: `True`
- Mutations: `0`

Output:

```text
Primero:
Resumen del cliente Cam:
Estado general: Hay 4 proyectos, 7 tareas abiertas y 2 bloqueadas.
Pendientes importantes:
- Resolver integracion CRM | Proyecto: Automatizacion | Cliente: Cam | bloqueada, alta prioridad | Sin proxima accion definida
- Revisar indicadores | Proyecto: Dashboard comercial | Cliente: Cam | bloqueada, alta prioridad | Sin proxima accion definida
- Definir metricas | Proyecto: Dashboard comercial | Cliente: Cam | alta prioridad | Sin proxima accion definida
Bloqueos o riesgos: ya quedaron integrados arriba en las tareas destacadas.
Merece atencion: ya quedo sintetizado arriba para evitar repeticion.
Proximos pasos relevantes:
- Cerrar entregable comercial | Proyecto: Dashboard comercial | Cliente: Cam | vence hoy | Proximo paso: Validar KPI final con Cam
- Follow-up forecast | Proyecto: Dashboard ventas | Cliente: Cam | Proximo paso: Mandar forecast a Cam
- Armar checklist onboarding | Proyecto: Onboarding | Cliente: Cam | Proximo paso: Cerrar checklist inicial
Recomendacion: Primero destrabaria 'Resolver integracion CRM', porque hoy es el mayor freno operativo.

Despues:
Lo que yo haria con Cam:
Estado general: Hay 4 proyectos y 7 tareas abiertas. Priorice donde veo mas impacto con este cliente.
Recomendaciones concretas:
- Primero: Resolver integracion CRM | Proyecto: Automatizacion | Cliente: Cam | Porque: esta bloqueada hace tiempo, es de alta prioridad y no tiene proxima accion, lleva bastante abierta, le falta seguimiento concreto | Recomendacion conservadora: definir proxima accion
- Como segunda opcion: Revisar indicadores | Proyecto: Dashboard comercial | Cliente: Cam | Porque: esta bloqueada hace tiempo, es de alta prioridad y no tiene proxima accion, lleva bastante abierta, le falta seguimiento concreto | Recomendacion conservadora: definir proxima accion
- Como tercera opcion: Actualizar indicadores de ventas | Proyecto: Dashboard ventas | Cliente: Cam | Porque: es de alta prioridad y no tiene proxima accion, lleva demasiado en progreso, le falta seguimiento concreto | Recomendacion conservadora: definir proxima accion
Recomendacion principal: Si tuviera que elegir una sola cosa, iria primero por 'Resolver integracion CRM'.
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_response: PASS (hay respuesta)
- should_have_audit_trace: PASS (audit trace presente)
- should_have_intent: PASS (intent=compound_query)
- should_have_subintent: PASS (subintents=['get_operational_summary', 'get_operational_recommendation', 'get_operational_summary', 'get_operational_recommendation'])
- should_have_compound_structure: PASS (estructura compuesta visible)

## CNT-001 - Resumen y followups conversacionales

- Category: continuity
- Severity: high
- Tags: daily, continuity, client, smoke_critical
- Status: PASS
- Turns: 3
- Expected checks: n/a
- Human review note: n/a

### Turn 1

- Input: `comentame en que andamos con Cam`
- Intent: `get_operational_summary`
- Scope: `client`
- Action status: `informational`
- Clarification: `False`
- Degraded: `False`
- Context reused: `False`
- Mutations: `0`

Output:

```text
Resumen del cliente Cam:
Estado general: Hay 4 proyectos, 7 tareas abiertas y 2 bloqueadas.
Pendientes importantes:
- Resolver integracion CRM | Proyecto: Automatizacion | Cliente: Cam | bloqueada, alta prioridad | Sin proxima accion definida
- Revisar indicadores | Proyecto: Dashboard comercial | Cliente: Cam | bloqueada, alta prioridad | Sin proxima accion definida
- Definir metricas | Proyecto: Dashboard comercial | Cliente: Cam | alta prioridad | Sin proxima accion definida
Bloqueos o riesgos: ya quedaron integrados arriba en las tareas destacadas.
Merece atencion: ya quedo sintetizado arriba para evitar repeticion.
Proximos pasos relevantes:
- Cerrar entregable comercial | Proyecto: Dashboard comercial | Cliente: Cam | vence hoy | Proximo paso: Validar KPI final con Cam
- Follow-up forecast | Proyecto: Dashboard ventas | Cliente: Cam | Proximo paso: Mandar forecast a Cam
- Armar checklist onboarding | Proyecto: Onboarding | Cliente: Cam | Proximo paso: Cerrar checklist inicial
Recomendacion: Primero destrabaria 'Resolver integracion CRM', porque hoy es el mayor freno operativo.
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_response: PASS (hay respuesta)
- should_have_scope: PASS (scope=client)
- should_contain_any: PASS (matches=['resumen del cliente cam', 'pendientes importantes'])

### Turn 2

- Input: `que me preocuparia`
- Intent: `get_followup_focus_summary`
- Scope: `contextual_client`
- Action status: `informational`
- Clarification: `False`
- Degraded: `False`
- Context reused: `True`
- Mutations: `0`

Output:

```text
Lo que me preocuparia de Cam:
Estado general: Hay 4 proyectos, 7 tareas abiertas y 4 con senales de friccion.
Senales de friccion:
- Resolver integracion CRM | Proyecto: Automatizacion | Cliente: Cam | Senales: bloqueada hace tiempo, abierta hace bastante sin cierre, alta prioridad sin proxima accion
- Revisar indicadores | Proyecto: Dashboard comercial | Cliente: Cam | Senales: bloqueada hace tiempo, abierta hace bastante sin cierre, alta prioridad sin proxima accion
- Actualizar indicadores de ventas | Proyecto: Dashboard ventas | Cliente: Cam | Senales: en progreso hace demasiado, abierta hace bastante sin cierre, alta prioridad sin proxima accion
- Definir metricas | Proyecto: Dashboard comercial | Cliente: Cam | Senales: abierta hace bastante sin cierre, alta prioridad sin proxima accion
Recomendacion: Primero destrabaria 'Resolver integracion CRM', porque combina bloqueo y senal temporal de atraso.
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_response: PASS (hay respuesta)
- should_have_context_reuse: PASS (reuso de contexto/snapshot)
- should_contain_any: PASS (matches=['lo que me preocuparia de cam', 'senales de friccion'])

### Turn 3

- Input: `que hiciste recien`
- Intent: `get_audit_trace_summary`
- Scope: `none`
- Action status: `informational`
- Clarification: `False`
- Degraded: `False`
- Context reused: `True`
- Mutations: `0`

Output:

```text
Recien te marque el foco de preocupacion principal. Hay 4 proyectos, 7 tareas abiertas y 4 con senales de friccion.
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_response: PASS (hay respuesta)
- should_have_audit_trace: PASS (audit trace presente)
- should_have_context_reuse: PASS (reuso de contexto/snapshot)
- should_contain_any: PASS (matches=['foco de preocupacion'])
- should_not_contain_any: PASS (matches=[])

## TMP-001 - Temporalidad diaria real

- Category: temporal
- Severity: medium
- Tags: daily, temporal, deadlines, smoke_critical
- Status: PASS
- Turns: 2
- Expected checks: n/a
- Human review note: n/a

### Turn 1

- Input: `que vence hoy`
- Intent: `get_due_tasks_summary`
- Scope: `today`
- Action status: `informational`
- Clarification: `False`
- Degraded: `False`
- Context reused: `False`
- Mutations: `0`

Output:

```text
Esto es lo que vence hoy:
- Cerrar entregable comercial | Vence: 2026-03-19 | Cliente: Cam | Proyecto: Dashboard comercial
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_response: PASS (hay respuesta)
- should_have_intent: PASS (intent=get_due_tasks_summary)
- should_contain_any: PASS (matches=['vence hoy', 'cerrar entregable comercial'])

### Turn 2

- Input: `que tengo para manana`
- Intent: `get_due_tasks_summary`
- Scope: `tomorrow`
- Action status: `informational`
- Clarification: `False`
- Degraded: `False`
- Context reused: `True`
- Mutations: `0`

Output:

```text
Esto es lo que tenes para mañana:
- Follow-up forecast | Vence: 2026-03-20 | Cliente: Cam | Proyecto: Dashboard ventas
- Armar checklist onboarding | Vence: 2026-03-20 | Cliente: Cam | Proyecto: Onboarding
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_response: PASS (hay respuesta)
- should_have_intent: PASS (intent=get_due_tasks_summary)
- should_contain_any: PASS (matches=['follow-up forecast', 'armar checklist onboarding'])

## SAFE-001 - Accion sin contexto seguro

- Category: safety
- Severity: critical
- Tags: daily, safety, no_mutation, smoke_critical
- Status: PASS
- Turns: 1
- Expected checks: n/a
- Human review note: n/a

### Turn 1

- Input: `cerrala`
- Intent: `update_task_status`
- Scope: `none`
- Action status: `blocked`
- Clarification: `True`
- Degraded: `True`
- Context reused: `False`
- Mutations: `0`

Output:

```text
No pude identificar con seguridad que tarea queres actualizar en esta conversacion actual.
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_not_mutate: PASS (mutaciones=0)
- should_not_invent_context: PASS (bloqueo seguro por contexto)
- should_have_action_status: PASS (action_status=blocked)
