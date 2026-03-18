from datetime import date

import streamlit as st

from app.services.client_service import get_all_clients
from app.services.project_service import get_all_projects
from app.services.task_service import (
    get_overdue_tasks,
    get_tasks_by_status,
    get_tasks_due_today,
)


def render_dashboard():
    st.title("Dashboard")

    today = date.today()

    clients = get_all_clients()
    projects = get_all_projects()

    project_map = {p.id: p.name for p in projects}
    project_to_client = {p.id: p.client_id for p in projects}
    client_map = {c.id: c.name for c in clients}

    overdue_tasks = get_overdue_tasks(today)
    today_tasks = get_tasks_due_today(today)
    in_progress_tasks = get_tasks_by_status("en_progreso")
    blocked_tasks = get_tasks_by_status("bloqueada")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Vencidas", len(overdue_tasks))

    with col2:
        st.metric("Para hoy", len(today_tasks))

    with col3:
        st.metric("En progreso", len(in_progress_tasks))

    with col4:
        st.metric("Bloqueadas", len(blocked_tasks))

    st.divider()

    def render_task_list(title: str, tasks: list):
        st.subheader(title)
        if tasks:
            for task in tasks:
                project_name = project_map.get(task.project_id, "Desconocido")
                client_name = client_map.get(project_to_client.get(task.project_id), "Desconocido")
                st.write(f"**{task.title}**")
                st.write(f"Cliente: {client_name}")
                st.write(f"Proyecto: {project_name}")
                st.write(f"Prioridad: {task.priority}")
                st.write(f"Vence: {task.due_date if task.due_date else 'Sin fecha'}")
                st.divider()
        else:
            st.write("No hay tareas en esta categoría.")

    render_task_list("Tareas vencidas", overdue_tasks)
    render_task_list("Tareas para hoy", today_tasks)
    render_task_list("Tareas en progreso", in_progress_tasks)
    render_task_list("Tareas bloqueadas", blocked_tasks)