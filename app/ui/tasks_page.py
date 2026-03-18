import streamlit as st

from app.services.client_service import get_all_clients
from app.services.project_service import get_all_projects, get_projects_by_client
from app.services.task_service import (
    create_task,
    get_all_tasks,
    get_tasks_by_project,
    update_task_context,
    update_task_main_fields,
    update_task_status,
)
from app.services.task_update_service import create_task_update, get_updates_by_task


def render_tasks_page():
    st.title("Tareas")

    clients = get_all_clients()
    projects = get_all_projects()

    if not projects:
        st.warning("Primero creá un proyecto")
        return

    st.subheader("Crear nueva tarea")

    project_options = {f"{p.name} ({p.id})": p.id for p in projects}
    selected_project = st.selectbox("Seleccionar proyecto", list(project_options.keys()))

    title = st.text_input("Título de la tarea")
    description = st.text_area("Descripción")
    priority = st.selectbox("Prioridad", ["baja", "media", "alta"])
    due_date = st.date_input("Fecha de vencimiento")

    if st.button("Crear tarea"):
        if title:
            create_task(
                project_id=project_options[selected_project],
                title=title,
                description=description,
                priority=priority,
                due_date=due_date,
            )
            st.success("Tarea creada correctamente")
            st.rerun()
        else:
            st.error("El título es obligatorio")

    st.divider()

    st.subheader("Lista de tareas")

    client_filter_options = {"Todos": None}
    for c in clients:
        client_filter_options[f"{c.name} ({c.id})"] = c.id

    selected_client_filter = st.selectbox(
        "Filtrar tareas por cliente",
        list(client_filter_options.keys()),
    )

    if client_filter_options[selected_client_filter] is None:
        filtered_projects = get_all_projects()
    else:
        filtered_projects = get_projects_by_client(client_filter_options[selected_client_filter])

    project_filter_options = {"Todos": None}
    for p in filtered_projects:
        project_filter_options[f"{p.name} ({p.id})"] = p.id

    selected_project_filter = st.selectbox(
        "Filtrar tareas por proyecto",
        list(project_filter_options.keys()),
    )

    if project_filter_options[selected_project_filter] is None:
        if client_filter_options[selected_client_filter] is None:
            tasks = get_all_tasks()
        else:
            project_ids = {p.id for p in filtered_projects}
            tasks = [t for t in get_all_tasks() if t.project_id in project_ids]
    else:
        tasks = get_tasks_by_project(project_filter_options[selected_project_filter])

    project_map = {p.id: p.name for p in projects}
    project_to_client = {p.id: p.client_id for p in projects}
    client_map = {c.id: c.name for c in clients}

    if not tasks:
        st.info("No hay tareas para mostrar.")
        return

    for task in tasks:
        client_name = client_map.get(project_to_client.get(task.project_id), "Desconocido")
        project_name = project_map.get(task.project_id, "Desconocido")

        with st.container():
            col1, col2 = st.columns([4, 2])

            with col1:
                st.write(f"### {task.title}")
                st.write(f"Cliente: {client_name}")
                st.write(f"Proyecto: {project_name}")
                st.write(f"Estado actual: {task.status}")
                st.write(f"Prioridad: {task.priority}")
                st.write(f"Vence: {task.due_date if task.due_date else 'Sin fecha'}")

                if task.description:
                    st.write(f"Descripción: {task.description}")

                st.write(f"Última nota: {task.last_note if task.last_note else 'Sin nota'}")
                st.write(f"Próxima acción: {task.next_action if task.next_action else 'Sin próxima acción'}")
                st.write(
                    f"Última actualización: {task.last_updated_at if task.last_updated_at else 'Sin actualizaciones'}"
                )

            with col2:
                new_status = st.selectbox(
                    f"Nuevo estado tarea {task.id}",
                    ["pendiente", "en_progreso", "bloqueada", "hecha"],
                    index=["pendiente", "en_progreso", "bloqueada", "hecha"].index(task.status),
                    key=f"status_{task.id}",
                )

                if st.button("Actualizar estado", key=f"update_status_{task.id}"):
                    update_task_status(task.id, new_status)
                    st.success(f"Estado de tarea {task.id} actualizado")
                    st.rerun()
            
            st.markdown("#### Editar datos principales")

            edit_title = st.text_input(
                f"Editar título tarea {task.id}",
                value=task.title,
                key=f"edit_title_{task.id}",
            )

            edit_description = st.text_area(
                f"Editar descripción tarea {task.id}",
                value=task.description if task.description else "",
                key=f"edit_description_{task.id}",
            )

            edit_priority = st.selectbox(
                f"Editar prioridad tarea {task.id}",
                ["baja", "media", "alta"],
                index=["baja", "media", "alta"].index(task.priority),
                key=f"edit_priority_{task.id}",
            )

            edit_due_date = st.date_input(
                f"Editar vencimiento tarea {task.id}",
                value=task.due_date,
                key=f"edit_due_date_{task.id}",
            )

            if st.button("Guardar datos principales", key=f"save_main_{task.id}"):
                if edit_title.strip():
                    update_task_main_fields(
                        task_id=task.id,
                        title=edit_title.strip(),
                        description=edit_description.strip() if edit_description else None,
                        priority=edit_priority,
                        due_date=edit_due_date,
                    )
                    st.success(f"Datos principales de tarea {task.id} actualizados")
                    st.rerun()
                else:
                    st.error("El título no puede estar vacío")

            st.markdown("#### Actualizar contexto de la tarea")

            new_last_note = st.text_area(
                f"Nueva última nota tarea {task.id}",
                value=task.last_note if task.last_note else "",
                key=f"last_note_{task.id}",
            )

            new_next_action = st.text_area(
                f"Nueva próxima acción tarea {task.id}",
                value=task.next_action if task.next_action else "",
                key=f"next_action_{task.id}",
            )

            if st.button("Guardar contexto", key=f"save_context_{task.id}"):
                update_task_context(
                    task_id=task.id,
                    last_note=new_last_note if new_last_note else None,
                    next_action=new_next_action if new_next_action else None,
                )
                st.success(f"Contexto de tarea {task.id} actualizado")
                st.rerun()

            st.markdown("#### Agregar update al historial")

            update_content = st.text_area(
                f"Nuevo update tarea {task.id}",
                key=f"update_content_{task.id}",
            )

            if st.button("Agregar update", key=f"add_update_{task.id}"):
                if update_content.strip():
                    create_task_update(
                        task_id=task.id,
                        content=update_content.strip(),
                        update_type="manual",
                        source="ui",
                    )
                    st.success(f"Update agregado a tarea {task.id}")
                    st.rerun()
                else:
                    st.error("El contenido del update no puede estar vacío")

            st.markdown("#### Historial de updates")

            updates = get_updates_by_task(task.id)

            if updates:
                for update in updates:
                    st.write(f"- [{update.created_at}] {update.content}")
            else:
                st.write("Todavía no hay updates registrados.")

            st.divider()