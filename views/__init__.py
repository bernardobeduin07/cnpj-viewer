"""
Pacote de Camada de Visão (UI/Streamlit) do CNPJ Viewer.
Contém os módulos desacoplados para renderização de cada aba do sistema.
"""
from views.company_view import renderizar_detalhes_empresa
from views.dashboard_view import render_dashboard_tab
from views.search_view import render_search_tab
from views.filter_view import render_filter_tab

__all__ = [
    "renderizar_detalhes_empresa",
    "render_dashboard_tab",
    "render_search_tab",
    "render_filter_tab",
]
