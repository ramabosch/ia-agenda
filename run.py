import streamlit as st

from app.db import init_db
from app.ui.clients_page import render_clients_page
from app.ui.dashboard import render_dashboard
from app.ui.projects_page import render_projects_page
from app.ui.tasks_page import render_tasks_page
from app.ui.ai_queries_page import render_ai_queries_page
from app.ui.conversation_page import render_conversation_page

init_db()

st.set_page_config(page_title="Agenda AI", layout="wide")

st.sidebar.title("Agenda AI")

page = st.sidebar.radio(
    "Navegación",
    ["Dashboard", "Clientes", "Proyectos", "Tareas", "Consultas IA", "Asistente"]
)

if page == "Dashboard":
    render_dashboard()

elif page == "Clientes":
    render_clients_page()

elif page == "Proyectos":
    render_projects_page()

elif page == "Tareas":
    render_tasks_page()

elif page == "Consultas IA":
    render_ai_queries_page()
    
elif page == "Asistente":
    render_conversation_page()