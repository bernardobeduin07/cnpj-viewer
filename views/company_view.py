"""
Módulo de Visualização: Detalhes da Empresa (Dossiê Completo).
Renderiza as 4 sub-abas analíticas de uma empresa selecionada:
1. Dados Cadastrais
2. Estabelecimentos (Matriz e Filiais)
3. Quadro Societário (QSA)
4. Enquadramento no Simples Nacional e MEI
"""
import sqlite3
import pandas as pd
import streamlit as st
from typing import Optional, Dict

from enrichment import (
    formatar_cnpj,
    formatar_moeda,
    formatar_data,
    formatar_cnae,
    formatar_natureza_juridica,
    formatar_qualificacao,
    formatar_endereco,
    formatar_telefone,
    PORTE_EMPRESA,
    SITUACAO_CADASTRAL,
    IDENTIFICADOR_MATRIZ,
    IDENTIFICADOR_SOCIO,
    FAIXA_ETARIA,
    OPCAO_SIMPLES_MEI
)


def renderizar_detalhes_empresa(
    conn: sqlite3.Connection,
    cnpj_limpo: str,
    apoio: Dict[str, Dict[str, str]],
    filial_destaque: Optional[Dict[str, str]] = None
) -> None:
    """
    Renderiza o dossiê empresarial completo dividido em 4 abas.
    
    Args:
        conn: Conexão ativa com o banco SQLite.
        cnpj_limpo: CNPJ básico (8 dígitos numéricos).
        apoio: Dicionário contendo as tabelas auxiliares em memória.
        filial_destaque: Dicionário opcional {'cnpj_ordem': '...', 'cnpj_dv': '...'} para destacar unidade pesquisada.
    """
    naturezas_map = apoio.get("naturezas", {})
    cnaes_map = apoio.get("cnaes", {})
    municipios_map = apoio.get("municipios", {})
    qualificacoes_map = apoio.get("qualificacoes", {})
    paises_map = apoio.get("paises", {})

    tab_empresa, tab_estabelecimentos, tab_socios, tab_simples = st.tabs([
        "🏢 Dados Cadastrais",
        "📍 Estabelecimentos",
        "👥 Quadro Societário",
        "📑 Simples Nacional & MEI"
    ])

    # ------------------------------------------------------------
    # Sub-Aba 1: Dados Cadastrais Principais
    # ------------------------------------------------------------
    with tab_empresa:
        df_emp = pd.read_sql_query(
            "SELECT * FROM Empresas WHERE cnpj_basico = ?", 
            conn, 
            params=(cnpj_limpo,)
        )
        if not df_emp.empty:
            emp = df_emp.iloc[0]
            st.markdown(f"### {emp.get('razao_social', 'Empresa')}")

            col1, col2, col3 = st.columns(3)
            col1.metric("🏢 CNPJ Básico", formatar_cnpj(emp.get("cnpj_basico")))
            col2.metric("💰 Capital Social", formatar_moeda(emp.get("capital_social")))
            porte_txt = PORTE_EMPRESA.get(str(emp.get("porte_empresa")), "Não informado")
            col3.metric("📊 Porte da Empresa", porte_txt)

            st.divider()

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Natureza Jurídica:**")
                st.info(formatar_natureza_juridica(emp.get("natureza_juridica"), naturezas_map))
            with c2:
                st.markdown("**Qualificação do Responsável:**")
                st.info(formatar_qualificacao(emp.get("qualificacao_responsavel"), qualificacoes_map))

            ente = emp.get("ente_federativo_responsavel")
            if ente and str(ente).strip() not in ("", "None", "nan"):
                st.caption(f"🏛️ **Ente Federativo Responsável:** `{ente}`")
        else:
            st.warning("Dados cadastrais principais não localizados na tabela de Empresas.")

    # ------------------------------------------------------------
    # Sub-Aba 2: Estabelecimentos (Matriz e Filiais)
    # ------------------------------------------------------------
    with tab_estabelecimentos:
        try:
            if filial_destaque:
                st.info(
                    f"🎯 **Unidade pesquisada diretamente:** Filial `{filial_destaque.get('cnpj_ordem')}-{filial_destaque.get('cnpj_dv')}`"
                )

            # Contagem ultraveloz usando o índice B-Tree idx_estab_cnpj_basico (< 1ms)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM Estabelecimentos WHERE cnpj_basico = ?", (cnpj_limpo,))
            total_estab = cur.fetchone()[0]

            if total_estab > 0:
                limite_exibicao = 200
                df_estab = pd.read_sql_query(
                    "SELECT * FROM Estabelecimentos WHERE cnpj_basico = ? ORDER BY identificador_matriz ASC, cnpj_ordem ASC LIMIT ?",
                    conn,
                    params=(cnpj_limpo, limite_exibicao)
                )

                if total_estab > limite_exibicao:
                    st.caption(
                        f"Total de unidades encontradas: **{total_estab:,}**. "
                        f"Exibindo as primeiras **{limite_exibicao}** unidades para navegação instantânea."
                    )
                else:
                    matrizes = (df_estab["identificador_matriz"] == "1").sum()
                    filiais = total_estab - matrizes
                    st.caption(f"Total de unidades encontradas: **{total_estab}** ({matrizes} Matriz, {filiais} Filiais)")

                linhas_enriquecidas = []
                for _, r in df_estab.iterrows():
                    cnpj_completo = formatar_cnpj(r.get("cnpj_basico"), r.get("cnpj_ordem"), r.get("cnpj_dv"))
                    tipo = IDENTIFICADOR_MATRIZ.get(str(r.get("identificador_matriz")), "Outro")
                    situacao = SITUACAO_CADASTRAL.get(str(r.get("situacao_cadastral")), str(r.get("situacao_cadastral") or "—"))
                    dt_sit = formatar_data(r.get("data_situacao_cadastral"))
                    dt_abert = formatar_data(r.get("data_inicio_atividade"))
                    cnae_desc = formatar_cnae(r.get("cnae_fiscal_principal"), cnaes_map)

                    cod_mun = str(r.get("municipio", "") or "").strip().zfill(4) if r.get("municipio") else ""
                    nome_mun = municipios_map.get(cod_mun, cod_mun)
                    uf_str = str(r.get("uf", "") or "").strip()
                    cidade_uf = f"{nome_mun}/{uf_str}".strip("/")

                    endereco = formatar_endereco(r, municipios_map)
                    contato = formatar_telefone(r.get("ddd_1"), r.get("telefone_1"))
                    email = str(r.get("correio_eletronico", "") or "").strip().lower()
                    if email and email not in ("none", "nan"):
                        contato = f"{contato} | {email}" if contato != "—" else email

                    nome_fantasia = str(r.get("nome_fantasia", "") or "").strip()
                    if nome_fantasia in ("none", "nan", ""):
                        nome_fantasia = "—"

                    linhas_enriquecidas.append({
                        "CNPJ": cnpj_completo,
                        "Tipo": tipo,
                        "Nome Fantasia": nome_fantasia,
                        "Situação": f"{situacao} ({dt_sit})" if dt_sit != "—" else situacao,
                        "Abertura": dt_abert,
                        "Cidade / UF": cidade_uf,
                        "CNAE Principal": cnae_desc,
                        "Endereço Completo": endereco,
                        "Contato": contato
                    })

                st.dataframe(pd.DataFrame(linhas_enriquecidas), use_container_width=True)
            else:
                st.info("Nenhum estabelecimento encontrado.")
        except Exception as erro:
            st.error(f"Erro ao buscar estabelecimentos: {erro}")

    # ------------------------------------------------------------
    # Sub-Aba 3: Quadro de Sócios e Administradores (QSA)
    # ------------------------------------------------------------
    with tab_socios:
        try:
            df_soc = pd.read_sql_query(
                "SELECT * FROM Socios WHERE cnpj_basico = ?",
                conn,
                params=(cnpj_limpo,)
            )
            if not df_soc.empty:
                st.caption(f"Total de sócios/administradores: **{len(df_soc)}**")

                linhas_socios = []
                for _, s in df_soc.iterrows():
                    tipo_soc = IDENTIFICADOR_SOCIO.get(str(s.get("identificador_socio")), "—")
                    qual = formatar_qualificacao(s.get("qualificacao_socio"), qualificacoes_map)
                    faixa = FAIXA_ETARIA.get(str(s.get("faixa_etaria")), "Não informada")
                    dt_entrada = formatar_data(s.get("data_entrada_sociedade"))

                    cod_pais = str(s.get("pais", "") or "").strip().zfill(3) if s.get("pais") else ""
                    nome_pais = paises_map.get(cod_pais, "Brasil") if cod_pais else "Brasil"

                    doc = str(s.get("cnpj_cpf_socio", "") or "").strip()
                    if doc in ("none", "nan", ""):
                        doc = "—"

                    rep_nome = str(s.get("nome_representante", "") or "").strip()
                    rep_qual = formatar_qualificacao(s.get("qualificacao_representante"), qualificacoes_map)
                    rep_info = f"{rep_nome} ({rep_qual})" if rep_nome and rep_nome not in ("none", "nan") else "—"

                    linhas_socios.append({
                        "Nome do Sócio": s.get("nome_socio", "—"),
                        "Tipo": tipo_soc,
                        "Documento": doc,
                        "Qualificação": qual,
                        "Entrada": dt_entrada,
                        "Faixa Etária": faixa,
                        "País": nome_pais,
                        "Representante Legal": rep_info
                    })

                st.dataframe(pd.DataFrame(linhas_socios), use_container_width=True)
            else:
                st.info("Nenhum sócio registrado nesta empresa.")
        except Exception as erro:
            st.error(f"Erro ao buscar sócios: {erro}")

    # ------------------------------------------------------------
    # Sub-Aba 4: Simples Nacional & MEI
    # ------------------------------------------------------------
    with tab_simples:
        try:
            df_sim = pd.read_sql_query(
                "SELECT * FROM Simples WHERE cnpj_basico = ?",
                conn,
                params=(cnpj_limpo,)
            )
            if not df_sim.empty:
                sim = df_sim.iloc[0]
                col_s1, col_s2 = st.columns(2)

                with col_s1:
                    st.subheader("Simples Nacional")
                    status_simples = OPCAO_SIMPLES_MEI.get(str(sim.get("opcao_simples")), "Não Optante")
                    if status_simples == "Optante":
                        st.success("✅ **Optante pelo Simples Nacional**")
                    else:
                        st.info("ℹ️ **Não Optante pelo Simples Nacional**")

                    dt_opcao_s = formatar_data(sim.get("data_opcao_simples"))
                    dt_exc_s = formatar_data(sim.get("data_exclusao_simples"))
                    st.markdown(f"📅 **Data de Opção:** `{dt_opcao_s}`")
                    if dt_exc_s != "—":
                        st.markdown(f"🚫 **Data de Exclusão:** `{dt_exc_s}`")

                with col_s2:
                    st.subheader("MEI (Microempreendedor Individual)")
                    status_mei = OPCAO_SIMPLES_MEI.get(str(sim.get("opcao_mei")), "Não Optante")
                    if status_mei == "Optante":
                        st.success("✅ **Optante pelo MEI**")
                    else:
                        st.info("ℹ️ **Não Optante pelo MEI**")

                    dt_opcao_m = formatar_data(sim.get("data_opcao_mei"))
                    dt_exc_m = formatar_data(sim.get("data_exclusao_mei"))
                    st.markdown(f"📅 **Data de Opção:** `{dt_opcao_m}`")
                    if dt_exc_m != "—":
                        st.markdown(f"🚫 **Data de Exclusão:** `{dt_exc_m}`")
            else:
                st.info("ℹ️ Informações de enquadramento no Simples Nacional / MEI não disponíveis para este CNPJ.")
        except Exception as erro:
            st.error(f"Erro ao consultar Simples Nacional: {erro}")
