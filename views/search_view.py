"""
Módulo de Visualização: Busca Direta por Empresa ou CNPJ.
Permite pesquisa higienizada e instantânea por:
- CNPJ Completo (14 dígitos, ex: 00.000.000/0001-91 ou 00000000000191)
- CNPJ Básico (8 dígitos, ex: 33.000.167 ou 33000167)
- Razão Social (Busca em 2 níveis com índice B-Tree < 1ms e fallback automático)
"""
import time
import sqlite3
import pandas as pd
import streamlit as st
from typing import Dict

from enrichment import (
    sanitizar_busca,
    formatar_cnpj,
    formatar_moeda,
    formatar_natureza_juridica,
    PORTE_EMPRESA
)
from views.company_view import renderizar_detalhes_empresa


def render_search_tab(conn: sqlite3.Connection, apoio: Dict[str, Dict[str, str]]) -> None:
    """
    Renderiza a aba de busca direta por CNPJ ou Razão Social.
    
    Args:
        conn: Conexão ativa com o banco SQLite.
        apoio: Dicionário contendo as tabelas de apoio em memória.
    """
    naturezas_map = apoio.get("naturezas", {})

    termo_busca = st.text_input(
        "🔍 Buscar por CNPJ ou Razão Social:",
        placeholder="Ex: 00.000.000/0001-91, 33000167 ou BANCO DO BRASIL"
    ).strip()

    if not termo_busca:
        st.info("💡 Digite o nome da empresa, o CNPJ básico (8 dígitos) ou o CNPJ completo (14 dígitos com ou sem pontuação).")
        return

    info_busca = sanitizar_busca(termo_busca)

    # ------------------------------------------------------------
    # 1. Busca por CNPJ Completo (14 dígitos)
    # ------------------------------------------------------------
    if info_busca["tipo"] == "CNPJ_14":
        st.caption(f"🔎 Reconhecido CNPJ completo de 14 dígitos: `{info_busca['termo_formatado']}`")
        with st.spinner("Buscando CNPJ..."):
            query_emp = """
                SELECT cnpj_basico, razao_social, natureza_juridica, capital_social, porte_empresa
                FROM Empresas WHERE cnpj_basico = ?
            """
            df_resultados = pd.read_sql_query(query_emp, conn, params=(info_busca["cnpj_basico"],))

        if not df_resultados.empty:
            st.success(f"Empresa localizada: **{df_resultados.iloc[0]['razao_social']}** ({info_busca['termo_formatado']})")
            renderizar_detalhes_empresa(
                conn,
                info_busca["cnpj_basico"],
                apoio,
                filial_destaque={"cnpj_ordem": info_busca["cnpj_ordem"], "cnpj_dv": info_busca["cnpj_dv"]}
            )
        else:
            # Fallback em Estabelecimentos
            df_estab_check = pd.read_sql_query(
                "SELECT cnpj_basico, nome_fantasia FROM Estabelecimentos WHERE cnpj_basico = ? AND cnpj_ordem = ? LIMIT 1",
                conn, params=(info_busca["cnpj_basico"], info_busca["cnpj_ordem"])
            )
            if not df_estab_check.empty:
                nome = df_estab_check.iloc[0]["nome_fantasia"] or f"Filial {info_busca['termo_formatado']}"
                st.info(f"Unidade localizada na base de estabelecimentos: **{nome}**")
                renderizar_detalhes_empresa(
                    conn,
                    info_busca["cnpj_basico"],
                    apoio,
                    filial_destaque={"cnpj_ordem": info_busca["cnpj_ordem"], "cnpj_dv": info_busca["cnpj_dv"]}
                )
            else:
                st.error(f"CNPJ `{info_busca['termo_formatado']}` não encontrado no banco de dados.")

    # ------------------------------------------------------------
    # 2. Busca por CNPJ Básico (8 dígitos)
    # ------------------------------------------------------------
    elif info_busca["tipo"] == "CNPJ_8":
        st.caption(f"🔎 Reconhecido CNPJ básico de 8 dígitos: `{info_busca['termo_formatado']}`")
        with st.spinner("Buscando CNPJ básico..."):
            query_emp = """
                SELECT cnpj_basico, razao_social, natureza_juridica, capital_social, porte_empresa
                FROM Empresas WHERE cnpj_basico = ?
            """
            df_resultados = pd.read_sql_query(query_emp, conn, params=(info_busca["cnpj_basico"],))

        if not df_resultados.empty:
            st.success(f"Empresa localizada: **{df_resultados.iloc[0]['razao_social']}** ({info_busca['termo_formatado']})")
            renderizar_detalhes_empresa(conn, info_busca["cnpj_basico"], apoio)
        else:
            # Fallback em Estabelecimentos
            df_estab_check = pd.read_sql_query(
                "SELECT cnpj_basico, nome_fantasia FROM Estabelecimentos WHERE cnpj_basico = ? LIMIT 1",
                conn, params=(info_busca["cnpj_basico"],)
            )
            if not df_estab_check.empty:
                nome = df_estab_check.iloc[0]["nome_fantasia"] or f"Empresa CNPJ Básico {info_busca['termo_formatado']}"
                st.info(f"Estabelecimento localizado para este CNPJ básico: **{nome}**")
                renderizar_detalhes_empresa(conn, info_busca["cnpj_basico"], apoio)
            else:
                st.error(f"CNPJ básico `{info_busca['termo_formatado']}` não encontrado no banco de dados.")

    # ------------------------------------------------------------
    # 3. Busca Textual por Razão Social
    # ------------------------------------------------------------
    else:
        if len(info_busca["termo"]) < 3:
            st.warning("⚠️ Digite pelo menos 3 caracteres para buscar por Razão Social.")
            return

        termo_pesquisa = info_busca["termo"].strip()
        busca_ampla = st.checkbox(
            "🔍 Qualquer parte do nome",
            value=False
        )

        with st.spinner("Buscando empresas por razão social..."):
            t_ini = time.time()
            query_nome = """
                SELECT cnpj_basico, razao_social, natureza_juridica, capital_social, porte_empresa
                FROM Empresas
                WHERE razao_social LIKE ?
                LIMIT 50
            """
            if not busca_ampla:
                # Nível 1: Prefixo indexado via idx_empresas_razao (< 1ms)
                df_resultados = pd.read_sql_query(query_nome, conn, params=(f"{termo_pesquisa}%",))
                if df_resultados.empty:
                    # Nível 2: Fallback automático se não houver prefixo exato
                    df_resultados = pd.read_sql_query(query_nome, conn, params=(f"%{termo_pesquisa}%",))
                    if not df_resultados.empty:
                        st.info(f"💡 Nenhuma empresa encontrada iniciando por '{termo_pesquisa}'. Exibindo correspondências parciais encontradas no nome.")
            else:
                df_resultados = pd.read_sql_query(query_nome, conn, params=(f"%{termo_pesquisa}%",))
            
            duracao_busca = time.time() - t_ini

        if df_resultados.empty:
            st.error(f"Nenhuma empresa encontrada com o termo `{termo_pesquisa}` (tempo de busca: **{duracao_busca:.3f}s**).")
        else:
            st.success(f"Encontrados **{len(df_resultados)}** resultado(s) em **{duracao_busca:.3f}s**.")
            df_exibicao = pd.DataFrame({
                "CNPJ Básico": df_resultados["cnpj_basico"].apply(formatar_cnpj),
                "Razão Social": df_resultados["razao_social"],
                "Natureza Jurídica": df_resultados["natureza_juridica"].apply(lambda c: formatar_natureza_juridica(c, naturezas_map)),
                "Capital Social": df_resultados["capital_social"].apply(formatar_moeda),
                "Porte": df_resultados["porte_empresa"].apply(lambda p: PORTE_EMPRESA.get(str(p), "Não informado"))
            })
            st.dataframe(df_exibicao, use_container_width=True)

            st.subheader("🔎 Detalhes da Empresa")
            opcoes = [f"{formatar_cnpj(row['cnpj_basico'])} — {row['razao_social']}" for _, row in df_resultados.iterrows()]
            selecionado = st.selectbox("Selecione uma empresa da lista:", opcoes)
            if selecionado:
                cnpj_selecionado = "".join(filter(str.isdigit, selecionado.split(" — ")[0]))[:8]
                renderizar_detalhes_empresa(conn, cnpj_selecionado, apoio)
