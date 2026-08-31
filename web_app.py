import sqlite3
import pandas as pd
import streamlit as st

from sql import NOME_DB

# Configuração da página
st.set_page_config(
    page_title="Consulta CNPJ",
    page_icon="🏢",
    layout="wide"
)

# Conexão com o banco
@st.cache_resource
def conectar():
    return sqlite3.connect(NOME_DB, check_same_thread=False)

conn = conectar()

# Verificar se o banco tem dados
def tabela_existe(nome: str) -> bool:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (nome,)
    )
    return cur.fetchone() is not None

if not tabela_existe("Empresas"):
    st.warning("Banco vazio. Execute `python main.py` primeiro.")
    st.stop()

# Header com métricas
st.title("Consulta de Empresas — CNPJ")

@st.cache_data(ttl=3600)
def contar_registros():
    total = conn.execute("SELECT COUNT(*) FROM Empresas").fetchone()[0]
    ativas = conn.execute("""
        SELECT COUNT(*) FROM Estabelecimentos 
        WHERE situacao_cadastral = '02'
    """).fetchone()[0]
    return total, ativas

total, ativas = contar_registros()
col1, col2 = st.columns(2)
col1.metric("Total de empresas", f"{total:,}")
col2.metric("Estabelecimentos ativos", f"{ativas:,}")

busca = st.text_input(
    "🔍 Buscar por razão social ou CNPJ básico:",
    placeholder="Ex: PETROBRAS ou 33000167"
)

if not busca:
    st.info("Digite um termo para buscar.")
    st.stop()

if len(busca) < 3:
    st.warning("Digite pelo menos 3 caracteres.")
    st.stop()

# Query principal
@st.cache_data(ttl=300)
def buscar(termo: str):
    query = """
        SELECT * FROM Empresas
        WHERE razao_social LIKE ? OR cnpj_basico = ?
        LIMIT 50
    """
    return pd.read_sql_query(
        query, conn, params=(f"%{termo}%", termo)
    )

with st.spinner("Buscando..."):
    df = buscar(busca)

if df.empty:
    st.error("Nenhum resultado encontrado.")
    st.stop()

st.success(f"Encontrados {len(df)} resultado(s).")

# Resultados em tabela
st.dataframe(df, use_container_width=True)

# Detalhes de uma empresa selecionada
cnpjs = df["cnpj_basico"].tolist()
selecionado = st.selectbox("Selecione um CNPJ para ver detalhes:", cnpjs)

if selecionado:
    tab_empresa, tab_estab, tab_socios = st.tabs([
        "Empresa", "Estabelecimentos", "Sócios"
    ])

    with tab_empresa:
        empresa = df[df["cnpj_basico"] == selecionado].iloc[0]
        col1, col2 = st.columns(2)
        col1.write(f"**Razão Social:** {empresa['razao_social']}")
        col1.write(f"**CNPJ Básico:** {empresa['cnpj_basico']}")
        col2.write(f"**Capital Social:** R\$ {empresa['capital_social']}")
        col2.write(f"**Porte:** {empresa['porte_empresa']}")

    with tab_estab:
        df_estab = pd.read_sql_query(
            "SELECT * FROM Estabelecimentos WHERE cnpj_basico = ?",
            conn, params=(selecionado,)
        )
        if df_estab.empty:
            st.info("Nenhum estabelecimento encontrado.")
        else:
            st.dataframe(df_estab, use_container_width=True)

    with tab_socios:
        df_socios = pd.read_sql_query(
            "SELECT * FROM Socios WHERE cnpj_basico = ?",
            conn, params=(selecionado,)
        )
        if df_socios.empty:
            st.info("Nenhum sócio encontrado.")
        else:
            st.dataframe(df_socios, use_container_width=True)