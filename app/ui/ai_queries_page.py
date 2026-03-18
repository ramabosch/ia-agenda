import streamlit as st

from app.services.client_service import get_active_clients
from app.services.project_service import get_all_projects, get_project_operational_summary
from app.services.task_service import get_all_tasks, get_open_tasks_by_client_id, get_task_operational_summary


def render_ai_queries_page():
    st.title("Consultas orientadas a IA")

    st.subheader("1. Clientes activos")

    active_clients = get_active_clients()

    if active_clients:
        for client in active_clients:
            st.write(f"- {client.name} (ID {client.id})")
    else:
        st.write("No hay clientes activos.")

    st.divider()

    st.subheader("2. Tareas abiertas por cliente")

    if active_clients:
        client_options = {f"{c.name} ({c.id})": c.id for c in active_clients}
        selected_client = st.selectbox(
            "Elegí un cliente para ver tareas abiertas",
            list(client_options.keys()),
            key="ai_client_select",
        )

        open_tasks = get_open_tasks_by_client_id(client_options[selected_client])

        if open_tasks:
            for task in open_tasks:
                project_name = task.project.name if getattr(task, "project", None) else "Desconocido"
                st.write(f"**{task.title}**")
                st.write(f"Estado: {task.status}")
                st.write(f"Prioridad: {task.priority}")
                st.write(f"Proyecto: {project_name}")
                st.divider()
        else:
            st.write("No hay tareas abiertas para ese cliente.")

    st.divider()

    st.subheader("3. Resumen operativo de una tarea")

    all_tasks = get_all_tasks()

    if all_tasks:
        task_options = {f"{t.title} ({t.id})": t.id for t in all_tasks}
        selected_task = st.selectbox(
            "Elegí una tarea",
            list(task_options.keys()),
            key="ai_task_select",
        )

        task_summary = get_task_operational_summary(task_options[selected_task])

        if task_summary:
            st.json(task_summary)

    st.divider()

    st.subheader("4. Resumen operativo de un proyecto")

    all_projects = get_all_projects()

    if all_projects:
        project_options = {f"{p.name} ({p.id})": p.id for p in all_projects}
        selected_project = st.selectbox(
            "Elegí un proyecto",
            list(project_options.keys()),
            key="ai_project_select",
        )

        project_summary = get_project_operational_summary(project_options[selected_project])

        if project_summary:
            st.json(project_summary)