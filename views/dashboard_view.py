"""
Módulo de Visualização: Panorama Geral & Estatísticas (Dashboard).
Renderiza os gráficos analíticos em Altair sobre os 138M+ de registros:
- Distribuição Geográfica (Top 10 UFs)
- Situação Cadastral das Unidades
- Distribuição por Porte Empresarial
- Top 10 Atividades Econômicas (CNAEs Principais)
- Painel de Manutenção e Recálculo Analítico
"""
import sqlite3
import pandas as pd
import altair as alt
import streamlit as st
from typing import Dict, Any

from sql import NOME_DB, atualizar_estatisticas_dashboard


def render_dashboard_tab(conn: sqlite3.Connection, dados_dashboard: Dict[str, Any]) -> None:
    """
    Renderiza a aba de estatísticas e gráficos do sistema.
    
    Args:
        conn: Conexão ativa com o banco SQLite.
        dados_dashboard: Dicionário preparado com DataFrames agregados.
    """
    st.subheader("📊 Panorama Geral do Cadastro Nacional de Empresas")
    st.markdown(
        "Visão analítica consolidada sobre o ecossistema empresarial brasileiro "
        "a partir dos microdados oficiais da Receita Federal."
    )

    # ------------------------------------------------------------
    # Linha 1 de Gráficos: Distribuição Geográfica & Situação Cadastral
    # Perfeitamente alinhados na horizontal e com mesmo height=340
    # ------------------------------------------------------------
    col_g1, col_g2 = st.columns(2, vertical_alignment="top")

    with col_g1:
        df_uf = dados_dashboard.get("df_uf")
        if df_uf is not None and not df_uf.empty:
            chart_uf = alt.Chart(df_uf).mark_bar(
                cornerRadiusTopRight=4, 
                cornerRadiusBottomRight=4, 
                size=18
            ).encode(
                x=alt.X("Estabelecimentos:Q", title="Total de Estabelecimentos", axis=alt.Axis(format="~s")),
                y=alt.Y("UF:N", sort="-x", axis=alt.Axis(title=None)),
                color=alt.Color("Estabelecimentos:Q", scale=alt.Scale(scheme="blues"), legend=None),
                tooltip=[
                    alt.Tooltip("Estado:N", title="Estado"),
                    alt.Tooltip("UF:N", title="UF"),
                    alt.Tooltip("Estabelecimentos:Q", title="Estabelecimentos", format=","),
                    alt.Tooltip("Porcentagem:Q", title="Participação (%)", format=".2f")
                ]
            ).properties(
                title=alt.TitleParams(
                    text="📍 Top 10 Estados (UFs) por Estabelecimentos", 
                    fontSize=15, 
                    anchor="start", 
                    offset=12
                ),
                height=340
            )
            st.altair_chart(chart_uf, use_container_width=True)
        else:
            st.info("Dados de UF não disponíveis.")

    with col_g2:
        df_sit = dados_dashboard.get("df_situacao")
        if df_sit is not None and not df_sit.empty:
            cor_map_sit = {
                "02 — ATIVA": "#28a745",
                "08 — BAIXADA": "#dc3545",
                "04 — INAPTA": "#fd7e14",
                "03 — SUSPENSA": "#ffc107",
                "01 — NULA": "#6c757d"
            }
            chart_sit = alt.Chart(df_sit).mark_bar(
                cornerRadiusTopRight=4, 
                cornerRadiusBottomRight=4, 
                size=18
            ).encode(
                x=alt.X("Estabelecimentos:Q", title="Total de Estabelecimentos", axis=alt.Axis(format="~s")),
                y=alt.Y("Situação:N", sort="-x", axis=alt.Axis(title=None)),
                color=alt.Color(
                    "Situação:N",
                    scale=alt.Scale(
                        domain=list(cor_map_sit.keys()),
                        range=list(cor_map_sit.values())
                    ),
                    legend=None
                ),
                tooltip=[
                    alt.Tooltip("Situação:N", title="Situação"),
                    alt.Tooltip("Estabelecimentos:Q", title="Total", format=","),
                    alt.Tooltip("Porcentagem:Q", title="% da Base", format=".2f")
                ]
            ).properties(
                title=alt.TitleParams(
                    text="📑 Situação Cadastral das Unidades", 
                    fontSize=15, 
                    anchor="start", 
                    offset=12
                ),
                height=340
            )
            st.altair_chart(chart_sit, use_container_width=True)
        else:
            st.info("Dados de situação cadastral não disponíveis.")

    st.divider()

    # ------------------------------------------------------------
    # Linha 2 de Gráficos: Porte Empresarial & Top Setores Econômicos (CNAEs)
    # ------------------------------------------------------------
    col_g3, col_g4 = st.columns(2, vertical_alignment="top")

    with col_g3:
        st.markdown("##### 🏢 Distribuição por Porte da Empresa")
        df_porte = dados_dashboard.get("df_porte")
        if df_porte is not None and not df_porte.empty:
            chart_porte = alt.Chart(df_porte).mark_arc(innerRadius=60).encode(
                theta=alt.Theta("Empresas:Q"),
                color=alt.Color(
                    "Porte:N", 
                    scale=alt.Scale(scheme="tableau10"), 
                    legend=alt.Legend(orient="bottom", title=None)
                ),
                tooltip=[
                    alt.Tooltip("Porte:N", title="Porte"),
                    alt.Tooltip("Empresas:Q", title="Total Empresas", format=","),
                    alt.Tooltip("Porcentagem:Q", title="% do Total", format=".2f")
                ]
            ).properties(height=340)
            st.altair_chart(chart_porte, use_container_width=True)
        else:
            st.info("Dados de porte não disponíveis.")

    with col_g4:
        st.markdown("##### 💼 Top 10 Atividades Econômicas (CNAE Principal)")
        df_cnae = dados_dashboard.get("df_cnae")
        if df_cnae is not None and not df_cnae.empty:
            chart_cnae = alt.Chart(df_cnae).mark_bar(
                cornerRadiusTopRight=4, 
                cornerRadiusBottomRight=4, 
                size=18
            ).encode(
                x=alt.X("Estabelecimentos:Q", title="Total de Estabelecimentos", axis=alt.Axis(format="~s")),
                y=alt.Y("Atividade Econômica:N", sort="-x", axis=alt.Axis(title=None)),
                color=alt.Color("Estabelecimentos:Q", scale=alt.Scale(scheme="tealblues"), legend=None),
                tooltip=[
                    alt.Tooltip("Atividade Econômica:N", title="Atividade"),
                    alt.Tooltip("Estabelecimentos:Q", title="Total", format=","),
                ]
            ).properties(height=340)
            st.altair_chart(chart_cnae, use_container_width=True)
        else:
            st.info("Dados de CNAE não disponíveis.")

    # ------------------------------------------------------------
    # Seção Operacional com Expander: Recálculo das Estatísticas
    # ------------------------------------------------------------
    with st.expander("⚙️ Gerenciamento e Recálculo Analítico da Base"):
        st.markdown(
            "As métricas e distribuições acima são mantidas em tabelas analíticas (`DashboardStats`) "
            "para garantir carregamento instantâneo sobre os 138 milhões de registros da base. "
            "Caso novos arquivos tenham sido importados, você pode forçar a sincronização dos totais clicando abaixo:"
        )
        if st.button("🔄 Recalcular Estatísticas da Base (execução em segundo plano)"):
            with st.spinner("Recalculando agregações sobre toda a base de dados..."):
                atualizar_estatisticas_dashboard(NOME_DB)
                st.cache_data.clear()
            st.success("Estatísticas recalculadas com sucesso!")
            st.rerun()
