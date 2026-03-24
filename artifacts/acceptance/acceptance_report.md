# Acceptance Suite Report

- Generated at: 2026-03-24T00:00:24.591718
- Scenarios: 29
- PASS: 29
- FAIL: 0
- PARTIAL: 0
- Gate status: APTO
- By category: {'friction': {'pass': 3, 'fail': 0, 'partial': 0, 'total': 3}, 'recommendation': {'pass': 4, 'fail': 0, 'partial': 0, 'total': 4}, 'clarification': {'pass': 1, 'fail': 0, 'partial': 0, 'total': 1}, 'compound': {'pass': 2, 'fail': 0, 'partial': 0, 'total': 2}, 'continuity': {'pass': 5, 'fail': 0, 'partial': 0, 'total': 5}, 'temporal': {'pass': 1, 'fail': 0, 'partial': 0, 'total': 1}, 'targeting': {'pass': 2, 'fail': 0, 'partial': 0, 'total': 2}, 'safety': {'pass': 2, 'fail': 0, 'partial': 0, 'total': 2}, 'agenda': {'pass': 8, 'fail': 0, 'partial': 0, 'total': 8}, 'planning': {'pass': 1, 'fail': 0, 'partial': 0, 'total': 1}}
- By severity: {'critical': {'pass': 5, 'fail': 0, 'partial': 0, 'total': 5}, 'high': {'pass': 9, 'fail': 0, 'partial': 0, 'total': 9}, 'medium': {'pass': 15, 'fail': 0, 'partial': 0, 'total': 15}}
- Filters: {'categories': [], 'severities': [], 'tags': []}

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

## REC-001 - Recomendacion de destrabe global

- Category: recommendation
- Severity: high
- Tags: daily, recommendation, unblock
- Status: PASS
- Turns: 1
- Expected checks: should_have_intent, should_contain_any
- Human review note: n/a

### Turn 1

- Input: `que destraba mas ahora`
- Intent: `get_operational_recommendation`
- Scope: `global`
- Action status: `informational`
- Clarification: `False`
- Degraded: `False`
- Context reused: `False`
- Mutations: `0`

Output:

```text
Lo que yo atacaria primero para destrabar mas ahora es:
Estado general: Hay 8 tareas abiertas y la recomendacion prioriza donde mas destrabe veo.
Recomendaciones concretas:
- Primero: Resolver integracion CRM | Proyecto: Automatizacion | Cliente: Cam | Porque: esta bloqueada hace tiempo, es de alta prioridad y no tiene proxima accion, lleva bastante abierta, le falta seguimiento concreto | Recomendacion conservadora: definir proxima accion
- Como segunda opcion: Revisar indicadores | Proyecto: Dashboard comercial | Cliente: Cam | Porque: esta bloqueada hace tiempo, es de alta prioridad y no tiene proxima accion, lleva bastante abierta, le falta seguimiento concreto | Recomendacion conservadora: definir proxima accion
- Como tercera opcion: Definir metricas | Proyecto: Dashboard comercial | Cliente: Cam | Porque: es de alta prioridad y no tiene proxima accion, lleva bastante abierta, le falta seguimiento concreto | Recomendacion conservadora: definir proxima accion
Recomendacion principal: Yo intentaria destrabar primero 'Resolver integracion CRM', porque hoy parece la jugada con mas impacto.
Proyectos donde pondria foco despues:
- Automatizacion (Cam) | Score: 475 | Mejor foco: Resolver integracion CRM
- Dashboard comercial (Cam) | Score: 475 | Mejor foco: Revisar indicadores
Cliente donde veo mas impacto operativo: Cam (Resolver integracion CRM).
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_response: PASS (hay respuesta)
- should_have_audit_trace: PASS (audit trace presente)
- should_have_intent: PASS (intent=get_operational_recommendation)
- should_contain_any: PASS (matches=['destrabar', 'recomendacion principal'])

## REC-002 - Recomendacion de cierre diario

- Category: recommendation
- Severity: medium
- Tags: daily, recommendation, close
- Status: PASS
- Turns: 1
- Expected checks: n/a
- Human review note: n/a

### Turn 1

- Input: `que conviene cerrar hoy`
- Intent: `get_operational_recommendation`
- Scope: `global`
- Action status: `informational`
- Clarification: `False`
- Degraded: `False`
- Context reused: `False`
- Mutations: `0`

Output:

```text
Lo que mas conviene empujar para cerrar hoy es:
Estado general: Hay 8 tareas abiertas y la recomendacion prioriza lo mas cerrable con sentido operativo.
Recomendaciones concretas:
- Primero: Cerrar entregable comercial | Proyecto: Dashboard comercial | Cliente: Cam | Porque: vence hoy, ya tiene un siguiente paso concreto para empujar cierre | Proximo paso: Validar KPI final con Cam
- Como segunda opcion: Follow-up forecast | Proyecto: Dashboard ventas | Cliente: Cam | Porque: ya tiene un siguiente paso concreto para empujar cierre | Proximo paso: Mandar forecast a Cam
- Como tercera opcion: Armar checklist onboarding | Proyecto: Onboarding | Cliente: Cam | Porque: ya tiene un siguiente paso concreto para empujar cierre | Proximo paso: Cerrar checklist inicial
Recomendacion principal: Hoy intentaria cerrar 'Cerrar entregable comercial', porque es la opcion mas empujable con los datos actuales.
Proyectos donde pondria foco despues:
- Dashboard comercial (Cam) | Score: 150 | Mejor foco: Cerrar entregable comercial
- Dashboard ventas (Cam) | Score: 90 | Mejor foco: Follow-up forecast
Cliente donde veo mas impacto operativo: Cam (Cerrar entregable comercial).
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_response: PASS (hay respuesta)
- should_have_intent: PASS (intent=get_operational_recommendation)
- should_contain_any: PASS (matches=['cerrar hoy', 'primero:'])

## FRI-002 - Phrasing real de estancamiento

- Category: friction
- Severity: high
- Tags: daily, phrasing, friction
- Status: PASS
- Turns: 1
- Expected checks: n/a
- Human review note: n/a

### Turn 1

- Input: `que me viene estancando`
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
- should_have_intent: PASS (intent=get_operational_friction_summary)
- should_contain_any: PASS (matches=['friccion', 'estancamiento'])

## FRI-003 - Proyecto acumulando friccion

- Category: friction
- Severity: high
- Tags: daily, project, friction
- Status: PASS
- Turns: 1
- Expected checks: n/a
- Human review note: n/a

### Turn 1

- Input: `que proyecto esta acumulando friccion`
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
- should_have_intent: PASS (intent=get_operational_friction_summary)
- should_contain_any: PASS (matches=['proyectos con mas friccion', 'dashboard comercial'])

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

## REC-004 - Elegir una sola tarea

- Category: recommendation
- Severity: high
- Tags: daily, recommendation, prioritization
- Status: PASS
- Turns: 1
- Expected checks: n/a
- Human review note: n/a

### Turn 1

- Input: `si tuvieras que elegir una sola tarea, cual seria`
- Intent: `get_operational_recommendation`
- Scope: `global`
- Action status: `informational`
- Clarification: `False`
- Degraded: `False`
- Context reused: `False`
- Mutations: `0`

Output:

```text
Lo que yo haria primero ahora es:
Estado general: Hay 8 tareas abiertas y priorice donde veo mas impacto operativo inmediato.
Recomendaciones concretas:
- Primero: Resolver integracion CRM | Proyecto: Automatizacion | Cliente: Cam | Porque: esta bloqueada hace tiempo, es de alta prioridad y no tiene proxima accion, lleva bastante abierta, le falta seguimiento concreto | Recomendacion conservadora: definir proxima accion
- Como segunda opcion: Revisar indicadores | Proyecto: Dashboard comercial | Cliente: Cam | Porque: esta bloqueada hace tiempo, es de alta prioridad y no tiene proxima accion, lleva bastante abierta, le falta seguimiento concreto | Recomendacion conservadora: definir proxima accion
- Como tercera opcion: Actualizar indicadores de ventas | Proyecto: Dashboard ventas | Cliente: Cam | Porque: es de alta prioridad y no tiene proxima accion, lleva demasiado en progreso, le falta seguimiento concreto | Recomendacion conservadora: definir proxima accion
Recomendacion principal: Si tuviera que elegir una sola cosa, iria primero por 'Resolver integracion CRM'.
Proyectos donde pondria foco despues:
- Automatizacion (Cam) | Score: 600 | Mejor foco: Resolver integracion CRM
- Dashboard comercial (Cam) | Score: 600 | Mejor foco: Revisar indicadores
Cliente donde veo mas impacto operativo: Cam (Resolver integracion CRM).
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_response: PASS (hay respuesta)
- should_have_intent: PASS (intent=get_operational_recommendation)
- should_contain_any: PASS (matches=['si tuviera que elegir una sola cosa', 'resolver integracion crm'])

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

## CNT-002 - Cadena recomendacion, explicacion y reformulacion

- Category: continuity
- Severity: medium
- Tags: daily, continuity, recommendation, adaptive
- Status: PASS
- Turns: 4
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

### Turn 2

- Input: `por que esa`
- Intent: `get_recommendation_explanation`
- Scope: `none`
- Action status: `informational`
- Clarification: `False`
- Degraded: `False`
- Context reused: `True`
- Mutations: `0`

Output:

```text
Te dije primero 'Resolver integracion CRM' por estas razones:
- esta bloqueada hace tiempo
- es de alta prioridad y no tiene proxima accion
- lleva bastante abierta
- le falta seguimiento concreto
Y como no tiene proxima accion clara, ordenarla ayuda a bajar friccion rapido.
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_response: PASS (hay respuesta)
- should_have_context_reuse: PASS (reuso de contexto/snapshot)
- should_contain_any: PASS (matches=['resolver integracion crm'])

### Turn 3

- Input: `y despues de eso?`
- Intent: `get_followup_focus_summary`
- Scope: `none`
- Action status: `informational`
- Clarification: `False`
- Degraded: `False`
- Context reused: `True`
- Mutations: `0`

Output:

```text
Despues de eso, iria con 'Revisar indicadores'.
Porque: esta bloqueada hace tiempo, es de alta prioridad y no tiene proxima accion, lleva bastante abierta, le falta seguimiento concreto.
Antes de empujarla, definiria una proxima accion concreta.
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_response: PASS (hay respuesta)
- should_have_context_reuse: PASS (reuso de contexto/snapshot)
- should_contain_any: PASS (matches=['revisar indicadores'])

### Turn 4

- Input: `damelo mas ejecutivo`
- Intent: `get_rephrased_summary`
- Scope: `none`
- Action status: `informational`
- Clarification: `False`
- Degraded: `False`
- Context reused: `True`
- Mutations: `0`

Output:

```text
Version ejecutiva de Cam:
- Estado: Hay 4 proyectos y 7 tareas abiertas. Priorice donde veo mas impacto con este cliente.
- Foco: Resolver integracion CRM | Proyecto: Automatizacion | Cliente: Cam | esta bloqueada hace tiempo; es de alta prioridad y no tiene proxima accion; lleva bastante abierta | Sin proxima accion definida
- Decision: Despues de eso, iria con 'Revisar indicadores'.
Porque: esta bloqueada hace tiempo, es de alta prioridad y no tiene proxima accion, lleva bastante abierta, le falta seguimiento concreto.
Antes de empujarla, definiria una proxima accion concreta.
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_response: PASS (hay respuesta)
- should_have_context_reuse: PASS (reuso de contexto/snapshot)
- should_not_contain_any: PASS (matches=[])

## NAT-001 - Phrasing natural libre con resumen y recomendacion

- Category: continuity
- Severity: medium
- Tags: daily, continuity, natural_language
- Status: PASS
- Turns: 2
- Expected checks: n/a
- Human review note: n/a

### Turn 1

- Input: `que onda cam`
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
- should_have_intent: PASS (intent=get_operational_summary)
- should_have_scope: PASS (scope=client)
- should_contain_any: PASS (matches=['resumen del cliente cam', 'pendientes importantes'])

### Turn 2

- Input: `y ahora que`
- Intent: `get_operational_recommendation`
- Scope: `contextual_client`
- Action status: `informational`
- Clarification: `False`
- Degraded: `False`
- Context reused: `True`
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
- should_have_intent: PASS (intent=get_operational_recommendation)
- should_have_context_reuse: PASS (reuso de contexto/snapshot)
- should_contain_any: PASS (matches=['lo que yo haria con cam', 'recomendacion principal'])

## CTX-001 - Continuidad vaga mantiene la entidad activa

- Category: continuity
- Severity: medium
- Tags: daily, continuity, context
- Status: PASS
- Turns: 2
- Expected checks: n/a
- Human review note: n/a

### Turn 1

- Input: `que onda cam`
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

### Turn 2

- Input: `y de eso que hay?`
- Intent: `expand_context`
- Scope: `client`
- Action status: `informational`
- Clarification: `False`
- Degraded: `False`
- Context reused: `True`
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
- should_have_context_reuse: PASS (reuso de contexto/snapshot)
- should_contain_any: PASS (matches=['cam', 'pendientes importantes'])

## ORD-001 - Accion ordinal contextual sobre lista reciente

- Category: continuity
- Severity: high
- Tags: daily, continuity, ordinal
- Status: PASS
- Turns: 2
- Expected checks: n/a
- Human review note: n/a

### Turn 1

- Input: `decime las tareas de Cam`
- Intent: `get_open_tasks_by_client_name`
- Scope: `client`
- Action status: `None`
- Clarification: `False`
- Degraded: `False`
- Context reused: `False`
- Mutations: `0`

Output:

```text
Estas son las tareas abiertas de Cam:
- Revisar indicadores | Estado: bloqueada | Prioridad: alta | Proyecto: Dashboard comercial
- Cerrar entregable comercial | Estado: pendiente | Prioridad: media | Proyecto: Dashboard comercial
- Definir metricas | Estado: pendiente | Prioridad: alta | Proyecto: Dashboard comercial
- Actualizar indicadores de ventas | Estado: en_progreso | Prioridad: alta | Proyecto: Dashboard ventas
- Follow-up forecast | Estado: pendiente | Prioridad: media | Proyecto: Dashboard ventas
- Resolver integracion CRM | Estado: bloqueada | Prioridad: alta | Proyecto: Automatizacion
- Armar checklist onboarding | Estado: pendiente | Prioridad: media | Proyecto: Onboarding
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_response: PASS (hay respuesta)
- should_have_intent: PASS (intent=get_open_tasks_by_client_name)
- should_contain_any: PASS (matches=['revisar indicadores'])

### Turn 2

- Input: `Cerra la primera.`
- Intent: `clarify_entity_reference`
- Scope: `task`
- Action status: `executed`
- Clarification: `False`
- Degraded: `False`
- Context reused: `True`
- Mutations: `1`

Output:

```text
Listo: actualice la tarea 'Revisar indicadores'. Estado: 'bloqueada' -> 'hecha'.
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_response: PASS (hay respuesta)
- should_have_context_reuse: PASS (reuso de contexto/snapshot)
- should_have_action_status: PASS (action_status=executed)
- should_contain_any: PASS (matches=['actualice la tarea', 'revisar indicadores'])

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

## TGT-001 - Clarificacion por descriptor

- Category: targeting
- Severity: high
- Tags: daily, clarification, targeting
- Status: PASS
- Turns: 2
- Expected checks: n/a
- Human review note: n/a

### Turn 1

- Input: `dashboard`
- Intent: `clarify_entity_reference`
- Scope: `none`
- Action status: `blocked`
- Clarification: `True`
- Degraded: `True`
- Context reused: `False`
- Mutations: `0`

Output:

```text
Necesito que me aclares cual proyecto queres ver.
Estas son las coincidencias posibles que mejor matchean:
- 1. Dashboard comercial (proyecto | cliente: Cam)
- 2. Dashboard ventas (proyecto | cliente: Cam)

Si queres, te lo puedo resumir, marcar lo que preocupa o mostrar proximos pasos del que elijas.
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_clarify: PASS (clarificacion detectada)
- should_reference_candidate: PASS (candidate='dashboard')
- should_have_candidate_count: PASS (candidate_count=2)

### Turn 2

- Input: `el de ventas`
- Intent: `clarify_entity_reference`
- Scope: `task`
- Action status: `None`
- Clarification: `False`
- Degraded: `False`
- Context reused: `True`
- Mutations: `0`

Output:

```text
Resumen de la tarea 110:
Titulo: Actualizar indicadores de ventas
Cliente: Cam
Proyecto: Dashboard ventas
Estado actual: en_progreso
Prioridad: alta
Vence: Sin fecha
Ultima nota: Sin nota registrada
Proxima accion: Sin proxima accion definida
Updates registrados: 0
Ultimo update: No hay updates todavia
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_response: PASS (hay respuesta)
- should_have_context_reuse: PASS (reuso de contexto/snapshot)
- should_contain_any: PASS (matches=['dashboard ventas', 'cliente: cam'])

## TGT-002 - Clarificacion con contraste simple

- Category: targeting
- Severity: medium
- Tags: daily, clarification, contrast
- Status: PASS
- Turns: 2
- Expected checks: n/a
- Human review note: n/a

### Turn 1

- Input: `dashboard`
- Intent: `clarify_entity_reference`
- Scope: `none`
- Action status: `blocked`
- Clarification: `True`
- Degraded: `True`
- Context reused: `False`
- Mutations: `0`

Output:

```text
Necesito que me aclares cual proyecto queres ver.
Estas son las coincidencias posibles que mejor matchean:
- 1. Dashboard comercial (proyecto | cliente: Cam)
- 2. Dashboard ventas (proyecto | cliente: Cam)

Si queres, te lo puedo resumir, marcar lo que preocupa o mostrar proximos pasos del que elijas.
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_clarify: PASS (clarificacion detectada)
- should_have_candidate_count: PASS (candidate_count=2)

### Turn 2

- Input: `no el otro`
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
- should_have_context_reuse: PASS (reuso de contexto/snapshot)
- should_not_contain_any: PASS (matches=[])

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

## SAFE-002 - Update ambiguo sin mutacion

- Category: safety
- Severity: high
- Tags: daily, safety, clarification
- Status: PASS
- Turns: 1
- Expected checks: n/a
- Human review note: n/a

### Turn 1

- Input: `actualiza dashboard`
- Intent: `clarify_entity_reference`
- Scope: `none`
- Action status: `blocked`
- Clarification: `True`
- Degraded: `True`
- Context reused: `False`
- Mutations: `0`

Output:

```text
Necesito que me aclares cual proyecto queres ver.
Estas son las coincidencias posibles que mejor matchean:
- 1. Dashboard comercial (proyecto | cliente: Cam)
- 2. Dashboard ventas (proyecto | cliente: Cam)

Si queres, te lo puedo resumir, marcar lo que preocupa o mostrar proximos pasos del que elijas.
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_clarify: PASS (clarificacion detectada)
- should_not_mutate: PASS (mutaciones=0)
- should_have_action_status: PASS (action_status=blocked)

## AGD-001 - Agenda personal: crear evento para manana a las 10

- Category: agenda
- Severity: high
- Tags: daily, agenda, personal
- Status: PASS
- Turns: 1
- Expected checks: n/a
- Human review note: n/a

### Turn 1

- Input: `agendame manana a las 10 una reunion con Cam`
- Intent: `create_agenda_item`
- Scope: `agenda`
- Action status: `executed`
- Clarification: `False`
- Degraded: `False`
- Context reused: `False`
- Mutations: `1`

Output:

```text
Listo: guarde el evento 'reunion con cam'. Fecha: 2026-03-20. Hora: 10:00.
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_response: PASS (hay respuesta)
- should_have_intent: PASS (intent=create_agenda_item)
- should_have_action_status: PASS (action_status=executed)
- should_contain_any: PASS (matches=['guarde el evento', '10:00', 'reunion con cam'])

## AGD-002 - Agenda personal: agenda de hoy

- Category: agenda
- Severity: medium
- Tags: daily, agenda, personal
- Status: PASS
- Turns: 1
- Expected checks: n/a
- Human review note: n/a

### Turn 1

- Input: `que tengo para hoy`
- Intent: `get_agenda_items_summary`
- Scope: `agenda`
- Action status: `informational`
- Clarification: `False`
- Degraded: `False`
- Context reused: `False`
- Mutations: `0`

Output:

```text
Esto tenes en agenda para hoy:
- 10:00 | Evento | Reunion con Cam
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_response: PASS (hay respuesta)
- should_have_intent: PASS (intent=get_agenda_items_summary)
- should_have_scope: PASS (scope=agenda)
- should_contain_any: PASS (matches=['agenda para hoy', 'reunion con cam', '10:00'])

## AGD-003 - Agenda personal: agenda de manana

- Category: agenda
- Severity: medium
- Tags: daily, agenda, personal
- Status: PASS
- Turns: 1
- Expected checks: n/a
- Human review note: n/a

### Turn 1

- Input: `que tengo manana`
- Intent: `get_agenda_items_summary`
- Scope: `agenda`
- Action status: `informational`
- Clarification: `False`
- Degraded: `False`
- Context reused: `False`
- Mutations: `0`

Output:

```text
Esto tenes en agenda para mañana:
- 18:00 | Evento | Dentista
- Sin hora | Recordatorio | Revisar indicadores
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_response: PASS (hay respuesta)
- should_have_intent: PASS (intent=get_agenda_items_summary)
- should_have_scope: PASS (scope=agenda)
- should_contain_any: PASS (matches=['dentista', 'revisar indicadores'])

## AGD-004 - Agenda personal: lo que queda del dia

- Category: agenda
- Severity: medium
- Tags: daily, agenda, personal
- Status: PASS
- Turns: 1
- Expected checks: n/a
- Human review note: n/a

### Turn 1

- Input: `que me queda del dia`
- Intent: `get_agenda_items_summary`
- Scope: `agenda`
- Action status: `informational`
- Clarification: `False`
- Degraded: `False`
- Context reused: `False`
- Mutations: `0`

Output:

```text
Esto te queda del dia:
- 10:00 | Evento | Reunion con Cam
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_response: PASS (hay respuesta)
- should_have_intent: PASS (intent=get_agenda_items_summary)
- should_have_scope: PASS (scope=agenda)
- should_contain_any: PASS (matches=['te queda del dia', 'reunion con cam'])

## AGD-005 - Agenda personal: crear y mover evento

- Category: agenda
- Severity: medium
- Tags: daily, agenda, personal, crud
- Status: PASS
- Turns: 2
- Expected checks: n/a
- Human review note: n/a

### Turn 1

- Input: `agendame manana a las 10 una revision anual con Cam`
- Intent: `create_agenda_item`
- Scope: `agenda`
- Action status: `executed`
- Clarification: `False`
- Degraded: `False`
- Context reused: `False`
- Mutations: `1`

Output:

```text
Listo: guarde el evento 'revision anual con cam'. Fecha: 2026-03-20. Hora: 10:00.
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_action_status: PASS (action_status=executed)
- should_contain_any: PASS (matches=['guarde el evento', '10:00'])

### Turn 2

- Input: `move la revision anual a las 15`
- Intent: `update_agenda_item`
- Scope: `agenda`
- Action status: `executed`
- Clarification: `False`
- Degraded: `False`
- Context reused: `True`
- Mutations: `1`

Output:

```text
Listo: reprograme 'revision anual con cam'. Nueva fecha: 2026-03-20. Nueva hora: 15:00.
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_intent: PASS (intent=update_agenda_item)
- should_have_action_status: PASS (action_status=executed)
- should_contain_any: PASS (matches=['reprograme', '15:00'])

## AGD-006 - Agenda personal: crear y borrar evento

- Category: agenda
- Severity: medium
- Tags: daily, agenda, personal, crud
- Status: PASS
- Turns: 2
- Expected checks: n/a
- Human review note: n/a

### Turn 1

- Input: `agendame manana a las 10 una reunion con Cam`
- Intent: `create_agenda_item`
- Scope: `agenda`
- Action status: `executed`
- Clarification: `False`
- Degraded: `False`
- Context reused: `False`
- Mutations: `1`

Output:

```text
Listo: guarde el evento 'reunion con cam'. Fecha: 2026-03-20. Hora: 10:00.
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_action_status: PASS (action_status=executed)

### Turn 2

- Input: `borra eso`
- Intent: `delete_agenda_item`
- Scope: `agenda`
- Action status: `executed`
- Clarification: `False`
- Degraded: `False`
- Context reused: `True`
- Mutations: `1`

Output:

```text
Listo: elimine 'reunion con cam' de tu agenda.
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_intent: PASS (intent=delete_agenda_item)
- should_have_action_status: PASS (action_status=executed)
- should_contain_any: PASS (matches=['elimine', 'reunion con cam'])

## AGD-007 - Agenda personal: crear evento futuro relativo

- Category: agenda
- Severity: medium
- Tags: daily, agenda, personal, future
- Status: PASS
- Turns: 1
- Expected checks: n/a
- Human review note: n/a

### Turn 1

- Input: `agendá una reunion con alimentos para dentro de una semana a las 17:00`
- Intent: `create_agenda_item`
- Scope: `agenda`
- Action status: `executed`
- Clarification: `False`
- Degraded: `False`
- Context reused: `False`
- Mutations: `1`

Output:

```text
Listo: guarde el evento 'reunion con alimentos'. Fecha: 2026-03-26. Hora: 17:00.
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_intent: PASS (intent=create_agenda_item)
- should_have_action_status: PASS (action_status=executed)
- should_contain_any: PASS (matches=['guarde el evento', 'reunion con alimentos', '17:00'])

## AGD-008 - Agenda personal: horizonte de proximos dias

- Category: agenda
- Severity: medium
- Tags: daily, agenda, personal, future
- Status: PASS
- Turns: 1
- Expected checks: n/a
- Human review note: n/a

### Turn 1

- Input: `que tengo en los proximos dias`
- Intent: `get_agenda_items_summary`
- Scope: `planning`
- Action status: `informational`
- Clarification: `False`
- Degraded: `False`
- Context reused: `False`
- Mutations: `0`

Output:

```text
Esto se viene en los proximos dias:

- Manana 18:00 | Dentista
- Manana | Armar checklist onboarding | Tarea / Onboarding / Cam
- Manana | Follow-up forecast | Tarea / Dashboard ventas / Cam
- Manana | Revisar indicadores
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_intent: PASS (intent=get_agenda_items_summary)
- should_have_scope: PASS (scope=planning)
- should_contain_any: PASS (matches=['proximos dias', 'dentista', 'revisar indicadores'])

## PLN-001 - Planificacion futura combinada: agenda y tareas

- Category: planning
- Severity: medium
- Tags: daily, planning, future
- Status: PASS
- Turns: 3
- Expected checks: n/a
- Human review note: n/a

### Turn 1

- Input: `agendá una reunion con alimentos para dentro de una semana a las 17:00`
- Intent: `create_agenda_item`
- Scope: `agenda`
- Action status: `executed`
- Clarification: `False`
- Degraded: `False`
- Context reused: `False`
- Mutations: `1`

Output:

```text
Listo: guarde el evento 'reunion con alimentos'. Fecha: 2026-03-26. Hora: 17:00.
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_action_status: PASS (action_status=executed)

### Turn 2

- Input: `crea una tarea para seguimiento alimentos para dentro de una semana`
- Intent: `create_task`
- Scope: `none`
- Action status: `executed`
- Clarification: `False`
- Degraded: `False`
- Context reused: `True`
- Mutations: `1`

Output:

```text
Listo: cree la tarea nueva 'seguimiento alimentos'. Proyecto: Inbox. Prioridad: media. Vence: 2026-03-26.
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_action_status: PASS (action_status=executed)

### Turn 3

- Input: `que se viene`
- Intent: `get_agenda_items_summary`
- Scope: `planning`
- Action status: `informational`
- Clarification: `False`
- Degraded: `False`
- Context reused: `True`
- Mutations: `0`

Output:

```text
Esto se viene:

Proximos dias:
- Manana 18:00 | Dentista
- Manana | Armar checklist onboarding | Tarea / Onboarding / Cam
- Manana | Follow-up forecast | Tarea / Dashboard ventas / Cam
- Manana | Revisar indicadores
- 26/03 17:00 | reunion con alimentos
- 26/03 | seguimiento alimentos | Tarea / Inbox / Agenda AI
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_response: PASS (hay respuesta)
- should_contain_all: PASS (matches=['reunion con alimentos', 'seguimiento alimentos'] missing=[])

## CMP-002 - Compuesto con degradacion parcial

- Category: compound
- Severity: medium
- Tags: daily, compound, degradation
- Status: PASS
- Turns: 1
- Expected checks: n/a
- Human review note: n/a

### Turn 1

- Input: `por que esa y que vence hoy`
- Intent: `compound_query`
- Scope: `none`
- Action status: `degraded`
- Clarification: `False`
- Degraded: `True`
- Context reused: `False`
- Mutations: `0`

Output:

```text
Pude resolver una parte del pedido y la otra la deje aclarada.

Primero:
No tengo contexto aislado actual para continuar esa conversacion con seguridad.

Despues:
Esto es lo que vence hoy:
- Cerrar entregable comercial | Vence: 2026-03-19 | Cliente: Cam | Proyecto: Dashboard comercial
```

Checks:
- should_not_error: PASS (sin excepcion)
- should_have_response: PASS (hay respuesta)
- should_have_intent: PASS (intent=compound_query)
- should_have_partial_degradation: PASS (degraded_parts=['get_recommendation_explanation'])
- should_have_compound_structure: PASS (estructura compuesta visible)
