"""
CNPJ Viewer — Aplicação Principal (Streamlit).
Ponto de entrada do sistema web para consulta dos dados públicos de CNPJ da Receita Federal.
Arquitetura Modular desacoplada em Camada de Dados (sql), Enriquecimento (enrichment) e Visão (views).
"""
import os
import sqlite3
import streamlit as st

from download_manager import obter_gerenciador
from sql import NOME_DB
from enrichment import carregar_tabelas_apoio, carregar_dados_dashboard
from views import render_dashboard_tab, render_search_tab, render_filter_tab

# ============================================================
# 1. Configuração da Página
# ============================================================
st.set_page_config(
    page_title="Consulta de Empresas — CNPJ",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializa o processo de download/atualização automática em background
gerenciador = obter_gerenciador()
gerenciador.verificar_e_iniciar_automatico()

# ============================================================
# 2. Conexão com o Banco SQLite em Cache
# ============================================================
@st.cache_resource
def obter_conexao() -> sqlite3.Connection:
    """Retorna conexão persistente thread-safe com o banco de dados SQLite."""
    return sqlite3.connect(NOME_DB, check_same_thread=False)

def banco_inicializado() -> bool:
    """Verifica se o arquivo do banco existe e possui a tabela Empresas criada."""
    if not os.path.exists(NOME_DB) or os.path.getsize(NOME_DB) == 0:
        return False
    try:
        conn = obter_conexao()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Empresas'")
        return cur.fetchone() is not None
    except Exception:
        return False

# ============================================================
# 3. Barra Lateral: Monitoramento em Tempo Real
# ============================================================
with st.sidebar:
    st.header("⚙️ Status do Sistema")

    @st.fragment(run_every="1s")
    def painel_status_background() -> None:
        """Renderiza e executa a cada 1s o progresso de download/ingestão."""
        if gerenciador.verificando_api:
            st.info("🔄 Verificando atualizações na Receita Federal...")
        elif gerenciador.em_execucao:
            st.info(f"⏳ **{gerenciador.etapa_atual}:** `{gerenciador.arquivo_atual}`")

            # Barra 1: Progresso Geral
            total_arquivos = max(gerenciador.total, 1)
            concluidos = gerenciador.concluidos
            faltam = total_arquivos - concluidos
            prog_geral = min(max(concluidos / total_arquivos, 0.0), 1.0)
            st.progress(prog_geral, text=f"Arquivos processados: {concluidos}/{total_arquivos} (Faltam: {faltam})")

            # Barra 2: Progresso do Arquivo Atual em bytes
            lidos = gerenciador.arquivo_bytes_lidos
            total_bytes = max(gerenciador.arquivo_bytes_total, 1)
            prog_arquivo = min(max(lidos / total_bytes, 0.0), 1.0)

            mb_lidos = lidos / (1024 * 1024)
            mb_total = total_bytes / (1024 * 1024)
            porcentagem = prog_arquivo * 100
            st.progress(prog_arquivo, text=f"Progresso atual: {mb_lidos:.1f} MB / {mb_total:.1f} MB ({porcentagem:.1f}%)")

            if st.button("🛑 Cancelar Próximos", use_container_width=True):
                gerenciador.cancelar()
        else:
            st.success("✅ Base de dados 100% atualizada.")
            if st.button("🔄 Forçar Nova Verificação", use_container_width=True):
                gerenciador._ja_iniciou_auto = False
                gerenciador.verificando_api = False
                gerenciador.verificar_e_iniciar_automatico()
                st.rerun()

        # Histórico recente de logs
        if gerenciador.historico_logs:
            with st.expander("📋 Logs de Atualização", expanded=False):
                st.code("\n".join(gerenciador.historico_logs[-15:]), language="text")

    painel_status_background()

# ============================================================
# 4. Interface Principal: Cabeçalho e Métricas Rápidas
# ============================================================
st.title("🏢 Consulta de Empresas — CNPJ")

if not banco_inicializado():
    st.warning(
        "⚠️ O banco de dados está sendo construído pela primeira vez em segundo plano. "
        "Aguarde o download e a importação de alguns arquivos para conseguir buscar dados."
    )

conn = obter_conexao()

# Carregamento em memória das tabelas de apoio
apoio = carregar_tabelas_apoio(NOME_DB)
cnaes_map = apoio.get("cnaes", {})

# Carregamento das estatísticas consolidadas
dados_dashboard = carregar_dados_dashboard(NOME_DB, cnaes_map)
metricas = dados_dashboard.get("metricas", {})

total_emp = int(metricas.get("total_empresas", 0))
total_estab = int(metricas.get("total_estabelecimentos", 0))
total_soc = int(metricas.get("total_socios", 0))

# Cards de KPI no topo da página
col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("🏢 Total de Empresas Registradas", f"{total_emp:,}")
col_m2.metric("📍 Estabelecimentos Cadastrados", f"{total_estab:,}")
col_m3.metric("👥 Sócios e Administradores", f"{total_soc:,}")

st.divider()

# ============================================================
# 5. Navegação por Abas Modulares
# ============================================================
tab_dashboard, tab_busca, tab_filtros = st.tabs([
    "📊 Panorama Geral & Estatísticas",
    "🏢 Busca por Empresa ou CNPJ",
    "🎯 Filtros & Exploração de Mercado"
])

with tab_dashboard:
    render_dashboard_tab(conn, dados_dashboard)

with tab_busca:
    render_search_tab(conn, apoio)

with tab_filtros:
    render_filter_tab(conn, apoio)