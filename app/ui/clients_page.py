import streamlit as st

from app.services.client_service import create_client, get_all_clients


def render_clients_page():
    st.title("Clientes")

    st.subheader("Crear nuevo cliente")

    name = st.text_input("Nombre del cliente")
    company = st.text_input("Empresa")
    notes = st.text_area("Notas")

    if st.button("Crear cliente"):
        if name:
            create_client(name, company, notes)
            st.success("Cliente creado correctamente")
        else:
            st.error("El nombre es obligatorio")

    st.divider()

    st.subheader("Lista de clientes")

    clients = get_all_clients()

    for c in clients:
        st.write(f"{c.id} - {c.name} - {c.company}")