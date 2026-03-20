from __future__ import annotations

import json
import traceback
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from app.services.hybrid_parser_service import parse_user_query_hybrid
from app.services.project_service import (
    get_operational_friction_project_snapshot,
    get_operational_recommendation_project_snapshot,
)
from app.services.query_response_service import build_response_from_query
from app.services.task_service import (
    build_client_advanced_summary,
    build_friction_focus_from_tasks,
    build_missing_due_date_snapshot_from_tasks,
    build_operational_focus_from_tasks,
    build_recommendation_focus_from_tasks,
    build_temporal_task_snapshot_from_tasks,
)
from tests.helpers import make_client, make_project, make_project_summary, make_task, make_task_summary


TODAY = date(2026, 3, 19)


@dataclass
class ScenarioTurn:
    input_text: str
    checks: dict[str, Any] = field(default_factory=dict)
    note: str | None = None


@dataclass
class Scenario:
    scenario_id: str
    title: str
    category: str
    severity: str
    tags: list[str]
    turns: list[ScenarioTurn]
    expected_checks: list[str] = field(default_factory=list)
    description: str | None = None
    human_review_note: str | None = None


class ExitStackContext:
    def __init__(self, patches: list[Any]):
        self._patches = patches
        self._stack: ExitStack | None = None

    def __enter__(self):
        self._stack = ExitStack()
        for patcher in self._patches:
            self._stack.enter_context(patcher)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._stack is not None:
            self._stack.close()
        return False


class AcceptanceBackend:
    def __init__(self, *, today: date | None = None):
        self.today = today or TODAY
        self._mutation_counter = 0
        self._mutation_log: list[dict[str, Any]] = []
        self.clients: list[Any] = []
        self.projects: list[Any] = []
        self.tasks: list[Any] = []
        self._seed()

    def _seed(self) -> None:
        cam = make_client(1, "Cam")
        lumen = make_client(2, "Lumen")
        self.clients = [cam, lumen]

        dashboard_comercial = make_project(10, "Dashboard comercial", cam, description="Seguimiento comercial")
        dashboard_ventas = make_project(11, "Dashboard ventas", cam, description="Pipeline de ventas")
        automatizacion = make_project(12, "Automatizacion", cam, description="Automatizaciones clave")
        onboarding = make_project(13, "Onboarding", cam, description="Alta de clientes")
        ops_lumen = make_project(20, "Ops interno", lumen, description="Operaciones")
        self.projects = [dashboard_comercial, dashboard_ventas, automatizacion, onboarding, ops_lumen]

        self.tasks = [
            make_task(
                100,
                "Revisar indicadores",
                dashboard_comercial,
                status="bloqueada",
                priority="alta",
                last_note="Falta validacion del cliente",
                created_at=datetime(2026, 2, 10, 10, 0, 0),
                last_updated_at=datetime(2026, 2, 20, 10, 0, 0),
            ),
            make_task(
                101,
                "Cerrar entregable comercial",
                dashboard_comercial,
                status="pendiente",
                priority="media",
                due_date=self.today,
                next_action="Validar KPI final con Cam",
                last_note="Quedo para cierre final",
                created_at=datetime(2026, 3, 10, 9, 0, 0),
                last_updated_at=datetime(2026, 3, 16, 9, 0, 0),
            ),
            make_task(
                102,
                "Definir metricas",
                dashboard_comercial,
                status="pendiente",
                priority="alta",
                last_note="Falta bajar definicion",
                created_at=datetime(2026, 3, 1, 12, 0, 0),
                last_updated_at=datetime(2026, 3, 4, 12, 0, 0),
            ),
            make_task(
                110,
                "Actualizar indicadores de ventas",
                dashboard_ventas,
                status="en_progreso",
                priority="alta",
                created_at=datetime(2026, 2, 12, 12, 0, 0),
                last_updated_at=datetime(2026, 2, 25, 12, 0, 0),
            ),
            make_task(
                111,
                "Follow-up forecast",
                dashboard_ventas,
                status="pendiente",
                priority="media",
                due_date=self.today + timedelta(days=1),
                next_action="Mandar forecast a Cam",
                created_at=datetime(2026, 3, 11, 15, 0, 0),
                last_updated_at=datetime(2026, 3, 17, 15, 0, 0),
            ),
            make_task(
                120,
                "Resolver integracion CRM",
                automatizacion,
                status="bloqueada",
                priority="alta",
                last_note="Dependencia externa trabada",
                created_at=datetime(2026, 2, 15, 8, 0, 0),
                last_updated_at=datetime(2026, 2, 28, 8, 0, 0),
            ),
            make_task(
                130,
                "Armar checklist onboarding",
                onboarding,
                status="pendiente",
                priority="media",
                due_date=self.today + timedelta(days=1),
                next_action="Cerrar checklist inicial",
                created_at=datetime(2026, 3, 14, 8, 0, 0),
                last_updated_at=datetime(2026, 3, 18, 8, 0, 0),
            ),
            make_task(
                200,
                "Revisar proveedores",
                ops_lumen,
                status="pendiente",
                priority="baja",
                created_at=datetime(2026, 3, 9, 10, 0, 0),
                last_updated_at=datetime(2026, 3, 10, 10, 0, 0),
            ),
        ]

    @property
    def mutation_count(self) -> int:
        return self._mutation_counter

    @property
    def mutation_log(self) -> list[dict[str, Any]]:
        return list(self._mutation_log)

    def get_active_clients(self) -> list[Any]:
        return self.all_clients()

    def all_clients(self) -> list[Any]:
        return list(self.clients)

    def all_projects(self) -> list[Any]:
        return list(self.projects)

    def all_tasks(self) -> list[Any]:
        return list(self.tasks)

    def projects_by_client_id(self, client_id: int) -> list[Any]:
        return [project for project in self.projects if getattr(project, "client_id", None) == client_id]

    def tasks_by_client_id(self, client_id: int) -> list[Any]:
        return [task for task in self.tasks if getattr(getattr(task, "project", None), "client_id", None) == client_id]

    def open_tasks_by_client_id(self, client_id: int) -> list[Any]:
        return [task for task in self.tasks_by_client_id(client_id) if task.status != "hecha"]

    def tasks_by_project_id(self, project_id: int) -> list[Any]:
        return [task for task in self.tasks if getattr(task, "project_id", None) == project_id]

    def tasks_by_status(self, status: str) -> list[Any]:
        return [task for task in self.tasks if task.status == status]

    def task_operational_summary(self, task_id: int) -> dict | None:
        task = self._find_task(task_id)
        if not task:
            return None
        return make_task_summary(task)

    def project_operational_summary(self, project_id: int) -> dict | None:
        project = self._find_project(project_id)
        if not project:
            return None
        return make_project_summary(project)

    def project_advanced_summary(self, project_id: int) -> dict | None:
        project = self._find_project(project_id)
        if not project:
            return None
        summary = self.project_operational_summary(project_id)
        focus = build_operational_focus_from_tasks(project.tasks, today=self.today)
        return {
            "scope": "project",
            "project_id": project.id,
            "entity_name": project.name,
            "client_id": project.client.id if project.client else None,
            "client_name": project.client.name if project.client else "Desconocido",
            "status_overview": _project_status_overview(summary),
            "important_pending": focus["important_pending"],
            "risk_items": focus["risk_items"],
            "attention_items": focus["attention_items"],
            "next_steps": focus["next_steps"],
            "recommendation": focus["recommendation"],
            "heuristic": focus["heuristic"],
        }

    def client_advanced_summary(self, client_name: str, projects: list[Any], tasks: list[Any]) -> dict:
        return build_client_advanced_summary(client_name, projects, tasks, today=self.today)

    def friction_snapshot(self) -> dict:
        return build_friction_focus_from_tasks(self.tasks, today=self.today)

    def recommendation_snapshot(self, focus: str = "general") -> dict:
        return build_recommendation_focus_from_tasks(self.tasks, today=self.today, focus=focus)

    def friction_project_snapshot(self) -> dict:
        items = []
        for project in self.projects:
            focus = build_friction_focus_from_tasks(project.tasks, today=self.today)
            friction_tasks = focus["friction_tasks"]
            items.append(
                {
                    "project_id": project.id,
                    "project_name": project.name,
                    "client_id": project.client.id if project.client else None,
                    "client_name": project.client.name if project.client else "Desconocido",
                    "open_tasks": len([task for task in project.tasks if task.status != "hecha"]),
                    "friction_tasks": len(friction_tasks),
                    "blocked_tasks": len([task for task in project.tasks if task.status == "bloqueada"]),
                    "without_next_action": len(
                        [
                            task
                            for task in project.tasks
                            if task.status != "hecha" and not (task.next_action or "").strip()
                        ]
                    ),
                    "score": sum(item["friction_score"] for item in friction_tasks) or len(friction_tasks),
                }
            )
        prioritized = sorted(
            [item for item in items if item["open_tasks"] > 0],
            key=lambda item: (-item["score"], item["project_name"]),
        )
        return {
            "projects": items,
            "prioritized_projects": prioritized[:5],
            "heuristic": [
                "mas tareas con friccion primero",
                "bloqueadas y alta prioridad pesan mas",
            ],
        }

    def recommendation_project_snapshot(self, focus: str = "general") -> dict:
        items = []
        for project in self.projects:
            project_recommendation = build_recommendation_focus_from_tasks(project.tasks, today=self.today, focus=focus)
            recommendations = project_recommendation["recommendations"]
            top_score = recommendations[0]["recommendation_score"] if recommendations else 0
            items.append(
                {
                    "project_id": project.id,
                    "project_name": project.name,
                    "client_id": project.client.id if project.client else None,
                    "client_name": project.client.name if project.client else "Desconocido",
                    "open_tasks": len([task for task in project.tasks if task.status != "hecha"]),
                    "score": top_score,
                    "top_recommendation": (recommendations[0]["title"] if recommendations else None),
                }
            )
        prioritized = sorted(
            [item for item in items if item["open_tasks"] > 0],
            key=lambda item: (-item["score"], item["project_name"]),
        )
        return {
            "projects": items,
            "prioritized_projects": prioritized[:5],
            "heuristic": [
                "se prioriza el proyecto con la mejor jugada operativa disponible",
            ],
        }

    def temporal_snapshot(self, time_scope: str, temporal_focus: str | None = None) -> dict:
        return build_temporal_task_snapshot_from_tasks(
            self.tasks,
            time_scope=time_scope,
            today=self.today,
            temporal_focus=temporal_focus,
        )

    def missing_due_date_snapshot(self) -> dict:
        return build_missing_due_date_snapshot_from_tasks(self.tasks, today=self.today)

    def create_task(
        self,
        project_id: int,
        title: str,
        *,
        priority: str = "media",
        due_date: date | None = None,
        last_note: str | None = None,
        next_action: str | None = None,
    ) -> dict:
        project = self._find_project(project_id)
        if not project:
            return {"created": False, "error": "not_found"}
        task_id = max(task.id for task in self.tasks) + 1 if self.tasks else 1
        task = make_task(
            task_id,
            title,
            project,
            status="pendiente",
            priority=priority,
            due_date=due_date,
            last_note=last_note,
            next_action=next_action,
            created_at=datetime.combine(self.today, datetime.min.time()),
            last_updated_at=datetime.combine(self.today, datetime.min.time()),
        )
        self.tasks.append(task)
        self._record_mutation("create_task", {"task_id": task.id, "project_id": project_id, "title": title})
        return {
            "created": True,
            "task_id": task.id,
            "task_title": task.title,
            "project_id": task.project_id,
            "field": "task",
            "priority": task.priority,
            "next_action": task.next_action,
            "last_note": task.last_note,
            "task": task,
        }

    def add_project_note(self, project_id: int, note_content: str) -> dict:
        project = self._find_project(project_id)
        if not project:
            return {"updated": False, "error": "not_found"}
        old_value = project.description
        project.description = note_content if not old_value else f"{old_value.rstrip()}\n\nNota operativa: {note_content}"
        self._record_mutation("project_note", {"project_id": project_id, "note": note_content})
        return {
            "updated": True,
            "project_id": project.id,
            "project_name": project.name,
            "field": "description",
            "old_value": old_value,
            "new_value": project.description,
            "project": project,
        }

    def update_task_status(self, task_id: int, *, new_status: str, reason: str | None = None) -> dict:
        task = self._find_task(task_id)
        if not task:
            return {"updated": False, "error": "not_found", "field": "status"}
        old_value = task.status
        if old_value == new_status and not reason:
            return {
                "updated": False,
                "error": "no_change",
                "field": "status",
                "task_title": task.title,
                "old_value": old_value,
                "new_value": new_status,
            }
        task.status = new_status
        if reason:
            task.last_note = reason
        task.last_updated_at = datetime.combine(self.today, datetime.min.time())
        self._record_mutation("task_status", {"task_id": task_id, "new_status": new_status, "reason": reason})
        return {
            "updated": True,
            "task_id": task.id,
            "task_title": task.title,
            "field": "status",
            "old_value": old_value,
            "new_value": task.status,
            "reason": reason,
        }

    def update_task_priority(self, task_id: int, *, new_priority: str | None, priority_direction: str | None = None) -> dict:
        task = self._find_task(task_id)
        if not task:
            return {"updated": False, "error": "not_found", "field": "priority"}
        resolved_priority = new_priority or _next_priority(task.priority, priority_direction)
        if resolved_priority not in {"alta", "media", "baja"}:
            return {"updated": False, "error": "invalid_priority", "field": "priority"}
        old_value = task.priority
        if old_value == resolved_priority:
            return {
                "updated": False,
                "error": "no_change",
                "field": "priority",
                "task_title": task.title,
                "old_value": old_value,
                "new_value": resolved_priority,
            }
        task.priority = resolved_priority
        task.last_updated_at = datetime.combine(self.today, datetime.min.time())
        self._record_mutation("task_priority", {"task_id": task_id, "new_priority": resolved_priority})
        return {
            "updated": True,
            "task_id": task.id,
            "task_title": task.title,
            "field": "priority",
            "old_value": old_value,
            "new_value": task.priority,
        }

    def add_task_note(self, task_id: int, *, note_content: str) -> dict:
        task = self._find_task(task_id)
        if not task:
            return {"updated": False, "error": "not_found", "field": "last_note"}
        old_value = task.last_note
        task.last_note = note_content
        task.last_updated_at = datetime.combine(self.today, datetime.min.time())
        self._record_mutation("task_note", {"task_id": task_id, "note": note_content})
        return {
            "updated": True,
            "task_id": task.id,
            "task_title": task.title,
            "field": "last_note",
            "old_value": old_value,
            "new_value": task.last_note,
        }

    def update_task_next_action(self, task_id: int, *, next_action: str) -> dict:
        task = self._find_task(task_id)
        if not task:
            return {"updated": False, "error": "not_found", "field": "next_action"}
        old_value = task.next_action
        task.next_action = next_action
        task.last_updated_at = datetime.combine(self.today, datetime.min.time())
        self._record_mutation("task_next_action", {"task_id": task_id, "next_action": next_action})
        return {
            "updated": True,
            "task_id": task.id,
            "task_title": task.title,
            "field": "next_action",
            "old_value": old_value,
            "new_value": task.next_action,
        }

    def _record_mutation(self, mutation_type: str, payload: dict[str, Any]) -> None:
        self._mutation_counter += 1
        self._mutation_log.append({"type": mutation_type, **payload})

    def _find_task(self, task_id: int) -> Any | None:
        return next((task for task in self.tasks if task.id == task_id), None)

    def _find_project(self, project_id: int) -> Any | None:
        return next((project for project in self.projects if project.id == project_id), None)


def build_default_backend() -> AcceptanceBackend:
    return AcceptanceBackend(today=TODAY)


DEFAULT_SCENARIOS = [
    Scenario(
        scenario_id="FRI-001",
        title="Friccion global por atraso",
        category="friction",
        severity="critical",
        tags=["daily", "friction", "regression", "smoke_critical"],
        expected_checks=["should_have_intent", "should_have_action_status", "should_contain_any"],
        turns=[
            ScenarioTurn(
                "que esta frenado hace mucho",
                {
                    "should_not_error": True,
                    "should_have_response": True,
                    "should_have_audit_trace": True,
                    "should_have_intent": "get_operational_friction_summary",
                    "should_have_action_status": "informational",
                    "should_contain_any": ["friccion", "estancamiento"],
                },
            )
        ],
    ),
    Scenario(
        scenario_id="REC-001",
        title="Recomendacion de destrabe global",
        category="recommendation",
        severity="high",
        tags=["daily", "recommendation", "unblock"],
        expected_checks=["should_have_intent", "should_contain_any"],
        turns=[
            ScenarioTurn(
                "que destraba mas ahora",
                {
                    "should_not_error": True,
                    "should_have_response": True,
                    "should_have_audit_trace": True,
                    "should_have_intent": "get_operational_recommendation",
                    "should_contain_any": ["destrabar", "Recomendacion principal"],
                },
            )
        ],
    ),
    Scenario(
        scenario_id="REC-002",
        title="Recomendacion de cierre diario",
        category="recommendation",
        severity="medium",
        tags=["daily", "recommendation", "close"],
        turns=[
            ScenarioTurn(
                "que conviene cerrar hoy",
                {
                    "should_not_error": True,
                    "should_have_response": True,
                    "should_have_intent": "get_operational_recommendation",
                    "should_contain_any": ["cerrar hoy", "Primero:"],
                },
            )
        ],
    ),
    Scenario(
        scenario_id="FRI-002",
        title="Phrasing real de estancamiento",
        category="friction",
        severity="high",
        tags=["daily", "phrasing", "friction"],
        turns=[
            ScenarioTurn(
                "que me viene estancando",
                {
                    "should_not_error": True,
                    "should_have_response": True,
                    "should_have_intent": "get_operational_friction_summary",
                    "should_contain_any": ["friccion", "estancamiento"],
                },
            )
        ],
    ),
    Scenario(
        scenario_id="FRI-003",
        title="Proyecto acumulando friccion",
        category="friction",
        severity="high",
        tags=["daily", "project", "friction"],
        turns=[
            ScenarioTurn(
                "que proyecto esta acumulando friccion",
                {
                    "should_not_error": True,
                    "should_have_response": True,
                    "should_have_intent": "get_operational_friction_summary",
                    "should_contain_any": ["Proyectos con mas friccion", "Dashboard comercial"],
                },
            )
        ],
    ),
    Scenario(
        scenario_id="REC-003",
        title="Que haria ahora con un cliente",
        category="recommendation",
        severity="critical",
        tags=["daily", "client", "recommendation", "smoke_critical"],
        turns=[
            ScenarioTurn(
                "que harias ahora con Cam",
                {
                    "should_not_error": True,
                    "should_have_response": True,
                    "should_have_scope": "client",
                    "should_have_intent": "get_operational_recommendation",
                    "should_contain_any": ["Lo que yo haria con Cam", "Recomendacion principal"],
                },
            )
        ],
    ),
    Scenario(
        scenario_id="REC-004",
        title="Elegir una sola tarea",
        category="recommendation",
        severity="high",
        tags=["daily", "recommendation", "prioritization"],
        turns=[
            ScenarioTurn(
                "si tuvieras que elegir una sola tarea, cual seria",
                {
                    "should_not_error": True,
                    "should_have_response": True,
                    "should_have_intent": "get_operational_recommendation",
                    "should_contain_any": ["Si tuviera que elegir una sola cosa", "Resolver integracion CRM"],
                },
            )
        ],
    ),
    Scenario(
        scenario_id="CLR-001",
        title="Continuacion de clarificacion para creacion",
        category="clarification",
        severity="critical",
        tags=["daily", "clarification", "multi_turn", "safe_write", "smoke_critical"],
        expected_checks=["should_clarify", "should_have_context_reuse"],
        human_review_note="Reclasificado: la clarificacion de create expone opciones confiables en el texto, pero no garantiza una lista estructurada completa de candidatos para este flujo.",
        turns=[
            ScenarioTurn(
                "agrega una tarea a Cam para definir metricas",
                {
                    "should_not_error": True,
                    "should_clarify": True,
                    "should_not_mutate": True,
                    "should_contain_any": ["Dashboard comercial", "Dashboard ventas", "Automatizacion"],
                },
            ),
            ScenarioTurn(
                "en dashboard comercial",
                {
                    "should_not_error": True,
                    "should_have_response": True,
                    "should_have_scope": "project",
                    "should_have_context_reuse": True,
                    "should_not_mutate": True,
                    "should_contain_any": ["Resumen del proyecto Dashboard comercial", "Cliente: Cam"],
                },
            ),
        ],
    ),
    Scenario(
        scenario_id="CMP-001",
        title="Compuesto resumen mas recomendacion",
        category="compound",
        severity="critical",
        tags=["daily", "compound", "client", "smoke_critical"],
        turns=[
            ScenarioTurn(
                "resumime Cam y decime que harias primero",
                {
                    "should_not_error": True,
                    "should_have_response": True,
                    "should_have_audit_trace": True,
                    "should_have_intent": "compound_query",
                    "should_have_subintent": "get_operational_recommendation",
                    "should_have_compound_structure": True,
                },
            )
        ],
    ),
    Scenario(
        scenario_id="CNT-001",
        title="Resumen y followups conversacionales",
        category="continuity",
        severity="high",
        tags=["daily", "continuity", "client", "smoke_critical"],
        turns=[
            ScenarioTurn(
                "comentame en que andamos con Cam",
                {
                    "should_not_error": True,
                    "should_have_response": True,
                    "should_have_scope": "client",
                    "should_contain_any": ["Resumen del cliente Cam", "Pendientes importantes"],
                },
            ),
            ScenarioTurn(
                "que me preocuparia",
                {
                    "should_not_error": True,
                    "should_have_response": True,
                    "should_have_context_reuse": True,
                    "should_contain_any": ["Lo que me preocuparia de Cam", "Senales de friccion"],
                },
            ),
            ScenarioTurn(
                "que hiciste recien",
                {
                    "should_not_error": True,
                    "should_have_response": True,
                    "should_have_audit_trace": True,
                    "should_have_context_reuse": True,
                    "should_contain_any": ["Recien te respondi", "get_followup_focus_summary"],
                },
            ),
        ],
    ),
    Scenario(
        scenario_id="CNT-002",
        title="Cadena recomendacion, explicacion y reformulacion",
        category="continuity",
        severity="medium",
        tags=["daily", "continuity", "recommendation", "adaptive"],
        turns=[
            ScenarioTurn(
                "que harias ahora con Cam",
                {
                    "should_not_error": True,
                    "should_have_response": True,
                    "should_have_scope": "client",
                },
            ),
            ScenarioTurn(
                "por que esa",
                {
                    "should_not_error": True,
                    "should_have_response": True,
                    "should_have_context_reuse": True,
                    "should_contain_any": ["La razon principal", "Resolver integracion CRM"],
                },
            ),
            ScenarioTurn(
                "y despues de eso?",
                {
                    "should_not_error": True,
                    "should_have_response": True,
                    "should_have_context_reuse": True,
                    "should_contain_any": ["segunda opcion", "Revisar indicadores"],
                },
            ),
            ScenarioTurn(
                "damelo mas ejecutivo",
                {
                    "should_not_error": True,
                    "should_have_response": True,
                    "should_have_context_reuse": True,
                    "should_not_contain_any": ["Traceback", "error"],
                },
            ),
        ],
    ),
    Scenario(
        scenario_id="TMP-001",
        title="Temporalidad diaria real",
        category="temporal",
        severity="medium",
        tags=["daily", "temporal", "deadlines", "smoke_critical"],
        turns=[
            ScenarioTurn(
                "que vence hoy",
                {
                    "should_not_error": True,
                    "should_have_response": True,
                    "should_have_intent": "get_due_tasks_summary",
                    "should_contain_any": ["vence hoy", "Cerrar entregable comercial"],
                },
            ),
            ScenarioTurn(
                "que tengo para manana",
                {
                    "should_not_error": True,
                    "should_have_response": True,
                    "should_have_intent": "get_due_tasks_summary",
                    "should_contain_any": ["para manana", "Follow-up forecast", "Armar checklist onboarding"],
                },
            ),
        ],
    ),
    Scenario(
        scenario_id="TGT-001",
        title="Clarificacion por descriptor",
        category="targeting",
        severity="high",
        tags=["daily", "clarification", "targeting"],
        turns=[
            ScenarioTurn(
                "dashboard",
                {
                    "should_not_error": True,
                    "should_clarify": True,
                    "should_reference_candidate": "dashboard",
                    "should_have_candidate_count": 2,
                },
            ),
            ScenarioTurn(
                "el de ventas",
                {
                    "should_not_error": True,
                    "should_have_response": True,
                    "should_have_context_reuse": True,
                    "should_contain_any": ["Dashboard ventas", "Cliente: Cam"],
                },
            ),
        ],
    ),
    Scenario(
        scenario_id="TGT-002",
        title="Clarificacion con contraste simple",
        category="targeting",
        severity="medium",
        tags=["daily", "clarification", "contrast"],
        turns=[
            ScenarioTurn(
                "dashboard",
                {
                    "should_not_error": True,
                    "should_clarify": True,
                    "should_have_candidate_count": 2,
                },
            ),
            ScenarioTurn(
                "no el otro",
                {
                    "should_not_error": True,
                    "should_have_response": True,
                    "should_have_context_reuse": True,
                    "should_not_contain_any": ["Necesito que me aclares cual proyecto queres ver"],
                },
            ),
        ],
    ),
    Scenario(
        scenario_id="SAFE-001",
        title="Accion sin contexto seguro",
        category="safety",
        severity="critical",
        tags=["daily", "safety", "no_mutation", "smoke_critical"],
        turns=[
            ScenarioTurn(
                "cerrala",
                {
                    "should_not_error": True,
                    "should_not_mutate": True,
                    "should_not_invent_context": True,
                    "should_have_action_status": "blocked",
                },
            )
        ],
    ),
    Scenario(
        scenario_id="SAFE-002",
        title="Update ambiguo sin mutacion",
        category="safety",
        severity="high",
        tags=["daily", "safety", "clarification"],
        turns=[
            ScenarioTurn(
                "actualiza dashboard",
                {
                    "should_not_error": True,
                    "should_clarify": True,
                    "should_not_mutate": True,
                    "should_have_action_status": "blocked",
                },
            )
        ],
    ),
    Scenario(
        scenario_id="CMP-002",
        title="Compuesto con degradacion parcial",
        category="compound",
        severity="medium",
        tags=["daily", "compound", "degradation"],
        turns=[
            ScenarioTurn(
                "por que esa y que vence hoy",
                {
                    "should_not_error": True,
                    "should_have_response": True,
                    "should_have_intent": "compound_query",
                    "should_have_partial_degradation": True,
                    "should_have_compound_structure": True,
                },
            )
        ],
    ),
]


def run_acceptance_suite(
    scenarios: list[Scenario] | None = None,
    *,
    output_dir: str | Path | None = None,
    category_filters: list[str] | None = None,
    severity_filters: list[str] | None = None,
    tag_filters: list[str] | None = None,
) -> dict[str, Any]:
    scenarios = scenarios or DEFAULT_SCENARIOS
    selected_scenarios = _filter_scenarios(
        scenarios,
        category_filters=category_filters,
        severity_filters=severity_filters,
        tag_filters=tag_filters,
    )
    report = {
        "generated_at": datetime.now().isoformat(),
        "scenario_count": len(selected_scenarios),
        "selected_filters": {
            "categories": category_filters or [],
            "severities": severity_filters or [],
            "tags": tag_filters or [],
        },
        "results": [],
    }

    for scenario in selected_scenarios:
        report["results"].append(run_scenario(scenario))

    report["summary"] = _suite_summary(report["results"])

    if output_dir is not None:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        json_path = output_path / "acceptance_report.json"
        markdown_path = output_path / "acceptance_report.md"
        json_path.write_text(json.dumps(_sanitize(report), ensure_ascii=False, indent=2), encoding="utf-8")
        markdown_path.write_text(render_markdown_report(report), encoding="utf-8")
        report["artifacts"] = {
            "json": str(json_path),
            "markdown": str(markdown_path),
        }

    return _sanitize(report)


def run_scenario(scenario: Scenario) -> dict[str, Any]:
    backend = build_default_backend()
    conversation_context: dict[str, Any] = {}
    turns_report: list[dict[str, Any]] = []
    scenario_errors: list[str] = []

    with _patch_backend(backend):
        for turn in scenario.turns:
            mutation_before = backend.mutation_count
            context_before = deepcopy(conversation_context)
            parsed: dict[str, Any] | None = None
            response = ""
            error = None

            try:
                parsed = parse_user_query_hybrid(turn.input_text)
                response = build_response_from_query(
                    parsed,
                    user_query=turn.input_text,
                    conversation_context=conversation_context,
                )
                conversation_context = parsed.get("_conversation_context") or conversation_context
            except Exception as exc:  # pragma: no cover
                error = "".join(traceback.format_exception(exc))
                scenario_errors.append(error)

            mutation_delta = backend.mutation_count - mutation_before
            turns_report.append(
                _build_turn_report(
                    turn=turn,
                    parsed=parsed,
                    response=response,
                    error=error,
                    context_before=context_before,
                    context_after=conversation_context,
                    mutation_delta=mutation_delta,
                    backend=backend,
                )
            )

    return {
        "id": scenario.scenario_id,
        "title": scenario.title,
        "category": scenario.category,
        "severity": scenario.severity,
        "tags": scenario.tags,
        "expected_checks": scenario.expected_checks,
        "description": scenario.description,
        "human_review_note": scenario.human_review_note,
        "status": _aggregate_status(turns_report),
        "turn_count": len(scenario.turns),
        "turns": turns_report,
        "errors": scenario_errors,
        "failed_checks": _collect_failed_checks(turns_report),
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Acceptance Suite Report",
        "",
        f"- Generated at: {report.get('generated_at')}",
        f"- Scenarios: {report.get('scenario_count')}",
        f"- PASS: {report.get('summary', {}).get('pass', 0)}",
        f"- FAIL: {report.get('summary', {}).get('fail', 0)}",
        f"- PARTIAL: {report.get('summary', {}).get('partial', 0)}",
        f"- Gate status: {report.get('summary', {}).get('gate_status', 'n/a')}",
        f"- By category: {report.get('summary', {}).get('by_category', {})}",
        f"- By severity: {report.get('summary', {}).get('by_severity', {})}",
        f"- Filters: {report.get('selected_filters', {})}",
        "",
    ]

    failing = report.get("summary", {}).get("failing_scenarios", [])
    if failing:
        lines.append("## Failing Or Partial")
        lines.append("")
        for item in failing:
            lines.append(f"- {item['id']} | {item['title']} | {item['status']} | checks fallidos: {', '.join(item['failed_checks']) or 'n/a'}")
        lines.append("")

    for scenario in report.get("results", []):
        lines.extend(
            [
                f"## {scenario['id']} - {scenario['title']}",
                "",
                f"- Category: {scenario['category']}",
                f"- Severity: {scenario['severity']}",
                f"- Tags: {', '.join(scenario.get('tags', []))}",
                f"- Status: {scenario['status']}",
                f"- Turns: {scenario['turn_count']}",
                f"- Expected checks: {', '.join(scenario.get('expected_checks', [])) or 'n/a'}",
                f"- Human review note: {scenario.get('human_review_note') or 'n/a'}",
                "",
            ]
        )
        for index, turn in enumerate(scenario.get("turns", []), start=1):
            lines.extend(
                [
                    f"### Turn {index}",
                    "",
                    f"- Input: `{turn['input']}`",
                    f"- Intent: `{turn.get('parsed_intent')}`",
                    f"- Scope: `{turn.get('scope')}`",
                    f"- Action status: `{turn.get('action_status')}`",
                    f"- Clarification: `{turn.get('clarification')}`",
                    f"- Degraded: `{turn.get('degraded')}`",
                    f"- Context reused: `{turn.get('context_reused')}`",
                    f"- Mutations: `{turn.get('mutation_delta')}`",
                    "",
                    "Output:",
                    "",
                    "```text",
                    turn.get("output") or "",
                    "```",
                    "",
                ]
            )
            if turn.get("checks"):
                lines.append("Checks:")
                for check in turn["checks"]:
                    lines.append(f"- {check['name']}: {check['status']} ({check['detail']})")
                lines.append("")
            if turn.get("error"):
                lines.extend(["Error:", "", "```text", turn["error"], "```", ""])

    return "\n".join(lines).strip() + "\n"


def _build_turn_report(
    *,
    turn: ScenarioTurn,
    parsed: dict[str, Any] | None,
    response: str,
    error: str | None,
    context_before: dict[str, Any],
    context_after: dict[str, Any],
    mutation_delta: int,
    backend: AcceptanceBackend,
) -> dict[str, Any]:
    resolved_references = (parsed or {}).get("_resolved_references") or {}
    audit_trace = (parsed or {}).get("_audit_trace")
    checks = _evaluate_checks(
        turn.checks,
        parsed=parsed or {},
        response=response,
        error=error,
        mutation_delta=mutation_delta,
        resolved_references=resolved_references,
        context_before=context_before,
        context_after=context_after,
    )
    return {
        "input": turn.input_text,
        "note": turn.note,
        "output": response,
        "error": error,
        "status": _turn_status(error, checks),
        "parsed_intent": (parsed or {}).get("intent"),
        "parsed_query": _extract_parsed_debug(parsed or {}),
        "resolved_references": _sanitize(resolved_references),
        "action_status": (audit_trace or {}).get("action_status"),
        "audit_trace": _sanitize(audit_trace),
        "clarification": bool((parsed or {}).get("_clarification_needed") or resolved_references.get("clarification_needed")),
        "degraded": _turn_is_degraded(parsed or {}, response, audit_trace),
        "scope": _turn_scope(parsed or {}, resolved_references),
        "context_reused": _context_reused(parsed or {}, resolved_references, context_before, context_after),
        "mutation_delta": mutation_delta,
        "mutation_log": backend.mutation_log,
        "checks": checks,
        "context_before": _sanitize(context_before),
        "context_after": _sanitize(context_after),
    }


def _evaluate_checks(
    configured_checks: dict[str, Any],
    *,
    parsed: dict[str, Any],
    response: str,
    error: str | None,
    mutation_delta: int,
    resolved_references: dict[str, Any],
    context_before: dict[str, Any],
    context_after: dict[str, Any],
) -> list[dict[str, Any]]:
    results = []
    for check_name, expected in configured_checks.items():
        passed, detail = _run_check(
            check_name,
            expected,
            parsed=parsed,
            response=response,
            error=error,
            mutation_delta=mutation_delta,
            resolved_references=resolved_references,
            context_before=context_before,
            context_after=context_after,
        )
        results.append({"name": check_name, "expected": expected, "status": "PASS" if passed else "FAIL", "detail": detail})
    return results


def _run_check(check_name: str, expected: Any, **kwargs) -> tuple[bool, str]:
    parsed = kwargs["parsed"]
    response = kwargs["response"]
    error = kwargs["error"]
    mutation_delta = kwargs["mutation_delta"]
    resolved = kwargs["resolved_references"]
    context_before = kwargs["context_before"]
    context_after = kwargs["context_after"]
    audit_trace = parsed.get("_audit_trace") or {}

    if check_name == "should_not_error":
        return error is None, "sin excepcion" if error is None else "hubo excepcion"
    if check_name == "should_have_response":
        return bool((response or "").strip()), "hay respuesta" if (response or "").strip() else "respuesta vacia"
    if check_name == "should_clarify":
        lowered = (response or "").lower()
        clarified = bool(
            parsed.get("_clarification_needed")
            or resolved.get("clarification_needed")
            or "aclar" in lowered
            or "opciones:" in lowered
            or "varios proyectos" in lowered
            or "decime en cual" in lowered
        )
        return clarified == bool(expected), "clarificacion detectada" if clarified else "sin clarificacion"
    if check_name == "should_not_mutate":
        return mutation_delta == 0, f"mutaciones={mutation_delta}"
    if check_name == "should_have_audit_trace":
        has_trace = isinstance(audit_trace, dict) and bool(audit_trace)
        return has_trace == bool(expected), "audit trace presente" if has_trace else "sin audit trace"
    if check_name == "should_have_scope":
        scope = _turn_scope(parsed, resolved)
        if isinstance(expected, str):
            return scope == expected, f"scope={scope}"
        return scope not in {None, 'none'}, f"scope={scope}"
    if check_name == "should_reference_candidate":
        expected_text = str(expected).lower()
        candidates = resolved.get("clarification_candidates") or parsed.get("_clarification_candidates") or []
        matches = any(expected_text in (item.get("name", "").lower()) for item in candidates)
        if not matches:
            matches = expected_text in (response or "").lower()
        return matches, f"candidate='{expected_text}'"
    if check_name == "should_use_context":
        used_context = bool(parsed.get("_used_context_to_disambiguate") or parsed.get("_used_previous_candidates") or resolved.get("used_context_to_disambiguate"))
        if not used_context and context_before:
            used_context = bool(context_after and context_after != context_before)
        return used_context == bool(expected), "uso contexto/candidatos previos" if used_context else "sin uso de contexto"
    if check_name == "should_have_context_reuse":
        reused = _context_reused(parsed, resolved, context_before, context_after)
        return reused == bool(expected), "reuso de contexto/snapshot" if reused else "sin reuso de contexto"
    if check_name == "should_not_invent_context":
        blocked = "no tengo contexto aislado actual" in (response or "").lower() or resolved.get("security_blocked") or parsed.get("_security_blocked")
        return blocked == bool(expected), "bloqueo seguro por contexto" if blocked else "sin bloqueo explicito"
    if check_name == "should_have_action_confirmation":
        confirmed = "listo:" in (response or "").lower()
        return confirmed == bool(expected), "confirmacion clara" if confirmed else "sin confirmacion"
    if check_name == "should_be_clear_confirmation":
        lowered = (response or "").lower()
        confirmed = "listo:" in lowered and any(token in lowered for token in ("cree", "actualice", "agregue"))
        return confirmed == bool(expected), "confirmacion clara y directa" if confirmed else "sin confirmacion clara"
    if check_name == "should_have_intent":
        intent = parsed.get("intent")
        return intent == expected, f"intent={intent}"
    if check_name == "should_have_subintent":
        subintents = [
            parsed.get("_compound_primary_intent"),
            parsed.get("_compound_secondary_intent"),
            *(parsed.get("_compound_resolved_parts") or []),
        ]
        return expected in [item for item in subintents if item], f"subintents={subintents}"
    if check_name == "should_have_action_status":
        status = audit_trace.get("action_status")
        return status == expected, f"action_status={status}"
    if check_name == "should_have_candidate_count":
        candidates = resolved.get("clarification_candidates") or parsed.get("_clarification_candidates") or []
        return len(candidates) >= int(expected), f"candidate_count={len(candidates)}"
    if check_name == "should_have_compound_structure":
        has_structure = "Primero:" in (response or "") and "Despues:" in (response or "")
        return has_structure == bool(expected), "estructura compuesta visible" if has_structure else "sin estructura compuesta"
    if check_name == "should_have_partial_degradation":
        degraded_parts = parsed.get("_compound_degraded_parts") or []
        has_partial = bool(degraded_parts) and bool(parsed.get("_compound_resolved_parts"))
        return has_partial == bool(expected), f"degraded_parts={degraded_parts}"
    if check_name == "should_contain_any":
        lowered = (response or "").lower()
        values = [str(item).lower() for item in expected]
        matched = [item for item in values if item in lowered]
        return bool(matched), f"matches={matched}"
    if check_name == "should_not_contain_any":
        lowered = (response or "").lower()
        values = [str(item).lower() for item in expected]
        matched = [item for item in values if item in lowered]
        return not matched, f"matches={matched}"
    return False, f"check no soportado: {check_name}"


def _turn_scope(parsed: dict[str, Any], resolved_references: dict[str, Any]) -> str | None:
    for key in (
        "_summary_scope",
        "_friction_scope",
        "_recommendation_scope",
        "_followup_scope",
        "_temporal_scope",
        "_resolver_scope",
    ):
        if parsed.get(key):
            return parsed[key]
    return resolved_references.get("scope")


def _context_reused(
    parsed: dict[str, Any],
    resolved_references: dict[str, Any],
    context_before: dict[str, Any],
    context_after: dict[str, Any],
) -> bool:
    if parsed.get("_used_context_to_disambiguate") or parsed.get("_used_previous_candidates"):
        return True
    if resolved_references.get("used_context_to_disambiguate"):
        return True
    if parsed.get("_compound_reused_snapshot"):
        return True
    return bool(context_before and context_after)


def _turn_is_degraded(parsed: dict[str, Any], response: str, audit_trace: dict[str, Any] | None) -> bool:
    if parsed.get("_clarification_needed"):
        return True
    if parsed.get("_adaptive_degraded") or parsed.get("_temporal_degraded"):
        return True
    if (audit_trace or {}).get("action_status") in {"blocked", "degraded"}:
        return True
    lowered = (response or "").lower()
    return any(marker in lowered for marker in ("no pude", "no tengo", "necesito que me aclares"))


def _turn_status(error: str | None, checks: list[dict[str, Any]]) -> str:
    if error:
        return "FAIL"
    failed = [check for check in checks if check["status"] == "FAIL"]
    if not failed:
        return "PASS"
    return "PARTIAL"


def _aggregate_status(turns: list[dict[str, Any]]) -> str:
    statuses = {turn["status"] for turn in turns}
    if statuses == {"PASS"}:
        return "PASS"
    if "FAIL" in statuses:
        return "FAIL"
    return "PARTIAL"


def _suite_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {
        "pass": 0,
        "fail": 0,
        "partial": 0,
        "by_category": {},
        "by_severity": {},
        "failing_scenarios": [],
    }
    for result in results:
        summary[result["status"].lower()] += 1
        summary["by_category"].setdefault(result["category"], {"pass": 0, "fail": 0, "partial": 0, "total": 0})
        summary["by_severity"].setdefault(result["severity"], {"pass": 0, "fail": 0, "partial": 0, "total": 0})
        summary["by_category"][result["category"]]["total"] += 1
        summary["by_category"][result["category"]][result["status"].lower()] += 1
        summary["by_severity"][result["severity"]]["total"] += 1
        summary["by_severity"][result["severity"]][result["status"].lower()] += 1
        if result["status"] != "PASS":
            summary["failing_scenarios"].append(
                {
                    "id": result["id"],
                    "title": result["title"],
                    "status": result["status"],
                    "failed_checks": result.get("failed_checks", []),
                }
            )
    summary["gate_status"] = "APTO" if summary["fail"] == 0 and summary["partial"] == 0 else "NO_APTO"
    return summary


def _collect_failed_checks(turns: list[dict[str, Any]]) -> list[str]:
    failed = []
    for turn in turns:
        for check in turn.get("checks", []):
            if check["status"] == "FAIL":
                failed.append(f"{turn['input']}::{check['name']}")
    return failed


def _filter_scenarios(
    scenarios: list[Scenario],
    *,
    category_filters: list[str] | None,
    severity_filters: list[str] | None,
    tag_filters: list[str] | None,
) -> list[Scenario]:
    category_filters = [item.lower() for item in (category_filters or [])]
    severity_filters = [item.lower() for item in (severity_filters or [])]
    tag_filters = [item.lower() for item in (tag_filters or [])]

    selected = []
    for scenario in scenarios:
        if category_filters and scenario.category.lower() not in category_filters:
            continue
        if severity_filters and scenario.severity.lower() not in severity_filters:
            continue
        if tag_filters and not any(tag.lower() in tag_filters for tag in scenario.tags):
            continue
        selected.append(scenario)
    return selected


def _extract_parsed_debug(parsed: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "intent",
        "entity_hint",
        "client_name",
        "project_name",
        "task_name",
        "new_status",
        "new_priority",
        "time_scope",
        "due_hint",
        "expected_scope",
        "_parser_source",
        "_parser_decision",
        "_resolved_references",
        "_clarification_needed",
        "_clarification_candidates",
        "_audit_trace",
        "_used_previous_candidates",
        "_used_context_to_disambiguate",
        "_compound_primary_intent",
        "_compound_secondary_intent",
        "_compound_resolved_parts",
        "_compound_degraded_parts",
        "_creation_real",
        "_creation_aborted",
        "_update_real",
        "_update_type",
        "_summary_scope",
        "_friction_scope",
        "_recommendation_scope",
        "_followup_scope",
        "_temporal_scope",
    ]
    return _sanitize({key: parsed.get(key) for key in keys if key in parsed})


def _patch_backend(backend: AcceptanceBackend):
    return ExitStackContext(
        [
            patch("app.services.reference_resolver.get_all_clients", side_effect=backend.all_clients),
            patch("app.services.reference_resolver.get_all_projects", side_effect=backend.all_projects),
            patch("app.services.reference_resolver.get_projects_by_client_id", side_effect=backend.projects_by_client_id),
            patch("app.services.reference_resolver.get_all_tasks", side_effect=backend.all_tasks),
            patch("app.services.reference_resolver.get_tasks_by_client_id", side_effect=backend.tasks_by_client_id),
            patch("app.services.reference_resolver.get_tasks_by_project_id", side_effect=backend.tasks_by_project_id),
            patch("app.services.query_response_service.get_active_clients", side_effect=backend.get_active_clients),
            patch("app.services.query_response_service.get_all_projects", side_effect=backend.all_projects),
            patch("app.services.query_response_service.get_projects_by_client_id", side_effect=backend.projects_by_client_id),
            patch("app.services.query_response_service.get_tasks_by_client_id", side_effect=backend.tasks_by_client_id),
            patch("app.services.query_response_service.get_tasks_by_project_id", side_effect=backend.tasks_by_project_id),
            patch("app.services.query_response_service.get_open_tasks_by_client_id", side_effect=backend.open_tasks_by_client_id),
            patch("app.services.query_response_service.get_tasks_by_status", side_effect=backend.tasks_by_status),
            patch("app.services.query_response_service.get_task_operational_summary", side_effect=backend.task_operational_summary),
            patch("app.services.query_response_service.get_project_operational_summary", side_effect=backend.project_operational_summary),
            patch("app.services.query_response_service.get_project_advanced_summary", side_effect=backend.project_advanced_summary),
            patch("app.services.query_response_service.build_client_advanced_summary", side_effect=backend.client_advanced_summary),
            patch("app.services.query_response_service.get_operational_friction_snapshot", side_effect=backend.friction_snapshot),
            patch("app.services.query_response_service.get_operational_recommendation_snapshot", side_effect=backend.recommendation_snapshot),
            patch("app.services.query_response_service.get_operational_friction_project_snapshot", side_effect=backend.friction_project_snapshot),
            patch("app.services.query_response_service.get_operational_recommendation_project_snapshot", side_effect=backend.recommendation_project_snapshot),
            patch("app.services.query_response_service.get_temporal_task_snapshot", side_effect=backend.temporal_snapshot),
            patch("app.services.query_response_service.get_missing_due_date_snapshot", side_effect=backend.missing_due_date_snapshot),
            patch(
                "app.services.query_response_service.build_temporal_task_snapshot_from_tasks",
                side_effect=lambda tasks, time_scope, today=None, temporal_focus=None: build_temporal_task_snapshot_from_tasks(
                    tasks,
                    time_scope=time_scope,
                    today=backend.today,
                    temporal_focus=temporal_focus,
                ),
            ),
            patch(
                "app.services.query_response_service.build_missing_due_date_snapshot_from_tasks",
                side_effect=lambda tasks, today=None: build_missing_due_date_snapshot_from_tasks(tasks, today=backend.today),
            ),
            patch("app.services.query_response_service.create_task_conversational", side_effect=backend.create_task),
            patch("app.services.query_response_service.add_project_note_conversational", side_effect=backend.add_project_note),
            patch("app.services.query_response_service.update_task_status_conversational", side_effect=backend.update_task_status),
            patch("app.services.query_response_service.update_task_priority_conversational", side_effect=backend.update_task_priority),
            patch("app.services.query_response_service.add_task_note_conversational", side_effect=backend.add_task_note),
            patch("app.services.query_response_service.update_task_next_action_conversational", side_effect=backend.update_task_next_action),
        ]
    )


def _sanitize(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, SimpleNamespace):
        return _sanitize(vars(value))
    if hasattr(value, "__dict__"):
        return _sanitize(vars(value))
    return str(value)


def _project_status_overview(summary: dict | None) -> str:
    if not summary:
        return "No pude resumir el estado del proyecto."
    return (
        f"Hay {summary['open_tasks']} tareas abiertas, "
        f"{summary['blocked_tasks']} bloqueadas y {summary['done_tasks']} cerradas."
    )


def _next_priority(current: str, direction: str | None) -> str:
    order = ["baja", "media", "alta"]
    if current not in order:
        return "media"
    index = order.index(current)
    if direction == "up":
        return order[min(index + 1, len(order) - 1)]
    if direction == "down":
        return order[max(index - 1, 0)]
    return current
