"""
Módulo de Visualização: Filtros & Exploração de Mercado.
Permite pesquisa multicritério sobre a base de estabelecimentos:
- Filtros por Estado (UF), Município, Situação Cadastral e Atividade Econômica (CNAE Principal)
- Otimização via SQLite Index Intersection (idx_estab_cnae e idx_estab_uf_mun)
- Exportação de dados para CSV compatível com Excel (utf-8-sig)
- Dossiê detalhado sob demanda (drilldown)
"""
import time
import sqlite3
import pandas as pd
import streamlit as st
from typing import Dict, Any, Tuple

from enrichment import (
    formatar_cnpj,
    formatar_data,
    formatar_cnae,
    formatar_endereco,
    formatar_telefone,
    obter_opcoes_municipios,
    obter_opcoes_cnaes,
    LISTA_UFS,
    SITUACAO_CADASTRAL,
    IDENTIFICADOR_MATRIZ
)
from views.company_view import renderizar_detalhes_empresa


def buscar_estabelecimentos_filtrados(
    conn: sqlite3.Connection,
    uf: str = "Todas",
    situacao: str = "Todas",
    municipio: str = "Todos",
    cnae: str = "Todos",
    limite: int = 25
) -> Tuple[pd.DataFrame, float]:
    """
    Executa consulta SQL parametrizada otimizada com índices compostos.
    
    Retorna o DataFrame resultante e o tempo de execução em segundos.
    """
    conditions = []
    params = []

    if uf and uf != "Todas":
        conditions.append("e.uf = ?")
        params.append(uf)
    if situacao and situacao != "Todas":
        conditions.append("e.situacao_cadastral = ?")
        params.append(situacao)
    if municipio and municipio != "Todos":
        conditions.append("e.municipio = ?")
        params.append(municipio)
    if cnae and cnae != "Todos":
        conditions.append("e.cnae_fiscal_principal = ?")
        params.append(cnae)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"""
        SELECT 
            e.cnpj_basico, e.cnpj_ordem, e.cnpj_dv,
            emp.razao_social, e.nome_fantasia,
            e.identificador_matriz, e.situacao_cadastral, e.data_situacao_cadastral,
            e.cnae_fiscal_principal, e.uf, e.municipio,
            e.tipo_logradouro, e.logradouro, e.numero, e.complemento, e.bairro, e.cep,
            e.ddd_1, e.telefone_1
        FROM Estabelecimentos e
        LEFT JOIN Empresas emp ON e.cnpj_basico = emp.cnpj_basico
        {where_clause}
        LIMIT ?
    """
    params.append(limite)

    t0 = time.time()
    df = pd.read_sql_query(query, conn, params=params)
    duracao = time.time() - t0
    return df, duracao


def render_filter_tab(conn: sqlite3.Connection, apoio: Dict[str, Dict[str, str]]) -> None:
    """
    Renderiza a aba de exploração e filtros avançados de mercado.
    
    Args:
        conn: Conexão ativa com o banco SQLite.
        apoio: Dicionário contendo as tabelas de apoio em memória.
    """
    municipios_map = apoio.get("municipios", {})
    cnaes_map = apoio.get("cnaes", {})

    st.subheader("🎯 Filtros Avançados de Estabelecimentos")
    st.markdown(
        "Explore o ecossistema de empresas filtrando por **UF (Estado)**, **Município**, "
        "**Situação Cadastral** e **Atividade Econômica (CNAE Principal)**."
    )

    col_f1, col_f2 = st.columns(2)

    with col_f1:
        filtro_uf = st.selectbox("📍 Estado (UF):", LISTA_UFS, index=0)

        opcoes_situacao = [
            ("Todas", "Todas as Situações"),
            ("02", "02 — ATIVA"),
            ("08", "08 — BAIXADA"),
            ("04", "04 — INAPTA"),
            ("03", "03 — SUSPENSA"),
            ("01", "01 — NULA")
        ]
        filtro_sit = st.selectbox("📑 Situação Cadastral:", opcoes_situacao, format_func=lambda x: x[1], index=1)

    with col_f2:
        opcoes_mun = obter_opcoes_municipios(municipios_map)
        filtro_mun = st.selectbox("🏙️ Município:", opcoes_mun, format_func=lambda x: x[1], index=0)

        opcoes_cnae = obter_opcoes_cnaes(cnaes_map)
        filtro_cnae = st.selectbox("💼 Atividade Econômica (CNAE Principal):", opcoes_cnae, format_func=lambda x: x[1], index=0)

    col_btn, col_lim = st.columns([3, 1])
    with col_lim:
        limite_filtro = st.selectbox("Quantidade máxima:", [25, 50, 100], index=0)
    with col_btn:
        st.write("")  # Alinhamento vertical com o selectbox
        executar_filtro = st.button("🔍 Aplicar Filtros", use_container_width=True, type="primary")

    if executar_filtro:
        st.session_state["filtro_executado"] = True
        st.session_state["params_filtro"] = {
            "uf": filtro_uf,
            "sit": filtro_sit[0],
            "mun": filtro_mun[0],
            "cnae": filtro_cnae[0],
            "limite": limite_filtro
        }

    if st.session_state.get("filtro_executado"):
        params = st.session_state["params_filtro"]

        with st.spinner("Consultando estabelecimentos na base de dados..."):
            df_filtrado, duracao = buscar_estabelecimentos_filtrados(
                conn=conn,
                uf=params["uf"],
                situacao=params["sit"],
                municipio=params["mun"],
                cnae=params["cnae"],
                limite=params["limite"]
            )

        if df_filtrado.empty:
            st.warning(
                f"⚠️ Nenhum estabelecimento encontrado com a combinação de filtros selecionada "
                f"(tempo de resposta: **{duracao:.3f}s**)."
            )
        else:
            st.success(f"Encontrados **{len(df_filtrado)}** estabelecimentos em **{duracao:.3f}s**.")

            linhas_formatadas = []
            for _, r in df_filtrado.iterrows():
                cnpj_fmt = formatar_cnpj(r.get("cnpj_basico"), r.get("cnpj_ordem"), r.get("cnpj_dv"))
                tipo_est = IDENTIFICADOR_MATRIZ.get(str(r.get("identificador_matriz")), "Outro")
                sit_desc = SITUACAO_CADASTRAL.get(str(r.get("situacao_cadastral")), str(r.get("situacao_cadastral") or "—"))
                dt_sit = formatar_data(r.get("data_situacao_cadastral"))
                cod_mun = str(r.get("municipio", "") or "").strip().zfill(4) if r.get("municipio") else ""
                nome_mun = municipios_map.get(cod_mun, cod_mun)
                cidade_uf = f"{nome_mun}/{r.get('uf', '')}".strip("/")
                cnae_desc = formatar_cnae(r.get("cnae_fiscal_principal"), cnaes_map)
                endereco = formatar_endereco(r, municipios_map)
                contato = formatar_telefone(r.get("ddd_1"), r.get("telefone_1"))

                razao = r.get("razao_social") or "—"
                fantasia = r.get("nome_fantasia")
                if fantasia is None or str(fantasia).strip().lower() in ("", "none", "nan"):
                    fantasia = "—"

                linhas_formatadas.append({
                    "CNPJ": cnpj_fmt,
                    "Razão Social": razao,
                    "Nome Fantasia": fantasia,
                    "Tipo": tipo_est,
                    "Situação": f"{sit_desc} ({dt_sit})" if dt_sit != "—" else sit_desc,
                    "Cidade / UF": cidade_uf,
                    "CNAE Principal": cnae_desc,
                    "Endereço": endereco,
                    "Contato": contato,
                    "_cnpj_basico": r.get("cnpj_basico")
                })

            df_tabela_filtro = pd.DataFrame(linhas_formatadas)

            # Botão de download CSV (exclui a coluna interna _cnpj_basico)
            colunas_visiveis = [c for c in df_tabela_filtro.columns if not c.startswith("_")]
            df_export = df_tabela_filtro[colunas_visiveis]
            st.dataframe(df_export, use_container_width=True)

            csv_bytes = df_export.to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button(
                label="📥 Baixar Resultados Filtrados (CSV)",
                data=csv_bytes,
                file_name=f"empresas_filtradas_{params['uf']}_{params['sit']}.csv",
                mime="text/csv",
                use_container_width=True
            )

            st.divider()
            st.subheader("🔎 Inspecionar Dossiê de uma Empresa dos Resultados")
            opcoes_inspecao = [
                f"{cnpj} — {razao}"
                for cnpj, razao in zip(df_tabela_filtro["CNPJ"], df_tabela_filtro["Razão Social"])
            ]
            empresa_escolhida = st.selectbox(
                "Selecione uma empresa da tabela acima para visualizar dados cadastrais, filiais e sócios:",
                opcoes_inspecao,
                index=None,
                placeholder="Clique aqui e selecione uma empresa para abrir o dossiê detalhado...",
                key="filtro_drilldown_select"
            )

            if empresa_escolhida:
                cnpj_escolhido = "".join(filter(str.isdigit, empresa_escolhida.split(" — ")[0]))[:8]
                renderizar_detalhes_empresa(conn, cnpj_escolhido, apoio)
