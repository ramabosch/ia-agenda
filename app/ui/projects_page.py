import streamlit as st

from app.services.client_service import get_all_clients
from app.services.project_service import create_project, get_all_projects, get_projects_by_client


def render_projects_page():
    st.title("Proyectos")

    clients = get_all_clients()

    if not clients:
        st.warning("Primero creá un cliente")
        return

    st.subheader("Crear nuevo proyecto")

    client_options = {f"{c.name} ({c.id})": c.id for c in clients}
    selected_client = st.selectbox("Seleccionar cliente", list(client_options.keys()))

    name = st.text_input("Nombre del proyecto")
    description = st.text_area("Descripción")

    if st.button("Crear proyecto"):
        if name:
            create_project(client_options[selected_client], name, description)
            st.success("Proyecto creado correctamente")
            st.rerun()
        else:
            st.error("El nombre es obligatorio")

    st.divider()

    st.subheader("Lista de proyectos")

    filter_options = {"Todos": None}
    for c in clients:
        filter_options[f"{c.name} ({c.id})"] = c.id

    selected_filter = st.selectbox("Filtrar por cliente", list(filter_options.keys()))

    if filter_options[selected_filter] is None:
        projects = get_all_projects()
    else:
        projects = get_projects_by_client(filter_options[selected_filter])

    client_map = {c.id: c.name for c in clients}

    if not projects:
        st.info("No hay proyectos para mostrar.")
        return

    for p in projects:
        st.write(f"**{p.name}**")
        st.write(f"Cliente: {client_map.get(p.client_id, 'Desconocido')}")
        st.write(f"Estado: {p.status}")
        if p.description:
            st.write(f"Descripción: {p.description}")
        st.divider()