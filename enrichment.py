import sqlite3
import re
from typing import Dict, Any, Optional, List, Tuple
import streamlit as st
import pandas as pd

# ============================================================
# 1. Mapeamentos Estáticos (Padrão Receita Federal)
# ============================================================

PORTE_EMPRESA: Dict[str, str] = {
    "00": "Não Informado",
    "01": "Microempresa (ME)",
    "03": "Empresa de Pequeno Porte (EPP)",
    "05": "Demais (Médio / Grande Porte)"
}

SITUACAO_CADASTRAL: Dict[str, str] = {
    "01": "NULA",
    "02": "ATIVA",
    "03": "SUSPENSA",
    "04": "INAPTA",
    "08": "BAIXADA"
}

IDENTIFICADOR_MATRIZ: Dict[str, str] = {
    "1": "MATRIZ",
    "2": "FILIAL"
}

IDENTIFICADOR_SOCIO: Dict[str, str] = {
    "1": "Pessoa Jurídica",
    "2": "Pessoa Física",
    "3": "Estrangeiro"
}

FAIXA_ETARIA: Dict[str, str] = {
    "0": "Não se aplica",
    "1": "0 a 12 anos",
    "2": "13 a 20 anos",
    "3": "21 a 30 anos",
    "4": "31 a 40 anos",
    "5": "41 a 50 anos",
    "6": "51 a 60 anos",
    "7": "61 a 70 anos",
    "8": "71 a 80 anos",
    "9": "Mais de 80 anos"
}

OPCAO_SIMPLES_MEI: Dict[str, str] = {
    "S": "Optante",
    "N": "Não Optante",
    "O": "Outros"
}


# ============================================================
# 2. Carregamento em Memória das Tabelas Auxiliares (Cacheado)
# ============================================================

@st.cache_data(show_spinner=False)
def carregar_tabelas_apoio(caminho_db: str) -> Dict[str, Dict[str, str]]:
    """
    Carrega as tabelas auxiliares em memória como dicionários O(1).
    O volume total é de menos de 1 MB, garantindo tradução instantânea sem joins SQL.
    """
    tabelas = ["Naturezas", "Cnaes", "Municipios", "Qualificacoes", "Motivos", "Paises"]
    lookup: Dict[str, Dict[str, str]] = {}
    try:
        with sqlite3.connect(caminho_db) as conn:
            cur = conn.cursor()
            for tab in tabelas:
                try:
                    rows = cur.execute(f"SELECT codigo, descricao FROM {tab}").fetchall()
                    lookup[tab.lower()] = {
                        str(r[0]).strip(): str(r[1]).strip()
                        for r in rows if r[0] is not None
                    }
                except Exception:
                    lookup[tab.lower()] = {}
    except Exception:
        for tab in tabelas:
            lookup[tab.lower()] = {}
    return lookup


# ============================================================
# 3. Funções de Formatação de Valores
# ============================================================

def formatar_cnpj(cnpj_basico: Optional[str], ordem: Optional[str] = None, dv: Optional[str] = None) -> str:
    """Formata CNPJ básico (8 dígitos) ou CNPJ completo (14 dígitos)."""
    if not cnpj_basico:
        return "—"
    b = str(cnpj_basico).strip().zfill(8)
    if ordem is not None and dv is not None:
        o = str(ordem).strip().zfill(4)
        d = str(dv).strip().zfill(2)
        return f"{b[:2]}.{b[2:5]}.{b[5:8]}/{o}-{d}"
    if len(b) == 14:
        return f"{b[:2]}.{b[2:5]}.{b[5:8]}/{b[8:12]}-{b[12:14]}"
    return f"{b[:2]}.{b[2:5]}.{b[5:8]}"


def formatar_moeda(valor: Any) -> str:
    """Formata strings monetárias como 'R$ 1.234.567,89'."""
    if valor is None or str(valor).strip() in ("", "None", "nan"):
        return "R$ 0,00"
    try:
        v_str = str(valor).strip().replace(",", ".")
        v = float(v_str)
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return f"R$ {valor}"


def formatar_data(data_str: Optional[str]) -> str:
    """Converte 'YYYYMMDD' ou 'YYYY-MM-DD' em 'DD/MM/YYYY'."""
    if not data_str or str(data_str).strip() in ("", "0", "00000000", "None", "nan"):
        return "—"
    s = str(data_str).strip()
    if len(s) == 8 and s.isdigit():
        ano, mes, dia = s[:4], s[4:6], s[6:]
        return f"{dia}/{mes}/{ano}"
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        ano, mes, dia = s.split("-")
        return f"{dia}/{mes}/{ano}"
    return s


def formatar_cep(cep_str: Optional[str]) -> str:
    """Converte '01001000' em '01001-000'."""
    if not cep_str or str(cep_str).strip() in ("", "None", "nan"):
        return "—"
    s = str(cep_str).strip().zfill(8)
    if len(s) == 8:
        return f"{s[:5]}-{s[5:]}"
    return s


def formatar_telefone(ddd: Optional[str], telefone: Optional[str]) -> str:
    """Formata DDD e número em '(DD) NNNN-NNNN'."""
    ddd_limpo = str(ddd).strip() if ddd and str(ddd).strip() not in ("None", "nan") else ""
    tel_limpo = str(telefone).strip() if telefone and str(telefone).strip() not in ("None", "nan") else ""
    if not tel_limpo:
        return "—"
    if ddd_limpo:
        return f"({ddd_limpo}) {tel_limpo}"
    return tel_limpo


def formatar_cnae(codigo: Optional[str], lookup_cnaes: Dict[str, str]) -> str:
    """Formata CNAE com máscara e descrição: '6201-5/01 — Desenvolvimento...'"""
    if not codigo or str(codigo).strip() in ("", "None", "nan"):
        return "—"
    cod = str(codigo).strip().zfill(7)
    desc = lookup_cnaes.get(cod, "Descrição não encontrada")
    if len(cod) == 7:
        cod_fmt = f"{cod[:4]}-{cod[4]}/{cod[5:7]}"
    else:
        cod_fmt = cod
    return f"{cod_fmt} — {desc}"


def formatar_natureza_juridica(codigo: Optional[str], lookup_naturezas: Dict[str, str]) -> str:
    """Formata Natureza Jurídica com código e descrição."""
    if not codigo or str(codigo).strip() in ("", "None", "nan"):
        return "—"
    cod = str(codigo).strip().zfill(4)
    desc = lookup_naturezas.get(cod, "Não informada")
    if len(cod) == 4:
        cod_fmt = f"{cod[:3]}-{cod[3]}"
    else:
        cod_fmt = cod
    return f"{cod_fmt} — {desc}"


def formatar_qualificacao(codigo: Optional[str], lookup_qualificacoes: Dict[str, str]) -> str:
    """Formata código de qualificação de responsável ou sócio."""
    if not codigo or str(codigo).strip() in ("", "None", "nan"):
        return "—"
    cod = str(codigo).strip().zfill(2)
    return lookup_qualificacoes.get(cod, f"Código {cod}")


def formatar_endereco(row: Any, lookup_municipios: Dict[str, str]) -> str:
    """Constrói endereço formatado completo a partir de uma linha de Estabelecimentos."""
    def limpar_campo(chave: str) -> str:
        v = row.get(chave)
        if v is None or pd.isna(v) or str(v).strip().lower() in ("", "none", "nan"):
            return ""
        return str(v).strip()

    tipo = limpar_campo("tipo_logradouro")
    logr = limpar_campo("logradouro")
    num = limpar_campo("numero")
    compl = limpar_campo("complemento")
    bairro = limpar_campo("bairro")
    uf = limpar_campo("uf")
    cod_mun = limpar_campo("municipio").zfill(4) if limpar_campo("municipio") else ""
    municipio = lookup_municipios.get(cod_mun, cod_mun) if cod_mun else ""
    cep = formatar_cep(row.get("cep"))

    partes_rua = []
    if tipo: partes_rua.append(tipo)
    if logr: partes_rua.append(logr)
    rua = " ".join(partes_rua) or "Logradouro não informado"

    num_str = num if num else "S/N"
    if compl: num_str += f" ({compl})"

    partes = [f"{rua}, {num_str}"]
    if bairro: partes.append(bairro)
    if municipio or uf: partes.append(f"{municipio}/{uf}".strip("/"))
    if cep and cep != "—": partes.append(f"CEP: {cep}")

    return " — ".join(partes)


# ============================================================
# 4. Higienização de Busca e Opções de Filtro (Itens 1 e 2)
# ============================================================

LISTA_UFS: List[str] = [
    "Todas", "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
    "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ",
    "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"
]

def sanitizar_busca(termo: str) -> Dict[str, Any]:
    """
    Higieniza e classifica o termo de busca:
    - Se contiver 14 dígitos (com ou sem máscara): CNPJ completo (básico + ordem + dv)
    - Se contiver 8 dígitos (com ou sem máscara): CNPJ básico
    - Caso contrário: Busca textual por Razão Social
    """
    t = termo.strip()
    digitos = re.sub(r"\D", "", t)

    if len(digitos) == 14:
        return {
            "tipo": "CNPJ_14",
            "cnpj_basico": digitos[:8],
            "cnpj_ordem": digitos[8:12],
            "cnpj_dv": digitos[12:14],
            "termo_formatado": formatar_cnpj(digitos[:8], digitos[8:12], digitos[12:14]),
            "valor_bruto": digitos
        }
    elif len(digitos) == 8:
        return {
            "tipo": "CNPJ_8",
            "cnpj_basico": digitos,
            "termo_formatado": formatar_cnpj(digitos),
            "valor_bruto": digitos
        }
    else:
        return {
            "tipo": "TEXTO",
            "termo": t.upper(),
            "valor_bruto": t
        }


@st.cache_data(show_spinner=False)
def obter_opcoes_municipios(lookup_municipios: Dict[str, str]) -> List[Tuple[str, str]]:
    """Retorna lista ordenada de tuplas (codigo, 'Nome do Município') para dropdowns."""
    itens = [("Todos", "Todos os Municípios")]
    municipios_ordenados = sorted(
        lookup_municipios.items(),
        key=lambda x: x[1]
    )
    for cod, nome in municipios_ordenados:
        itens.append((cod, f"{nome} ({cod})"))
    return itens


@st.cache_data(show_spinner=False)
def obter_opcoes_cnaes(lookup_cnaes: Dict[str, str]) -> List[Tuple[str, str]]:
    """Retorna lista ordenada de tuplas (codigo, 'CNAE formatado — Descrição') para dropdowns."""
    itens = [("Todos", "Todas as Atividades")]
    cnaes_ordenados = sorted(
        lookup_cnaes.items(),
        key=lambda x: x[0]
    )
    for cod, desc in cnaes_ordenados:
        cod_fmt = f"{cod[:4]}-{cod[4]}/{cod[5:7]}" if len(cod) == 7 else cod
        itens.append((cod, f"{cod_fmt} — {desc}"))
    return itens


@st.cache_data(ttl=3600, show_spinner=False)
def carregar_dados_dashboard(caminho_db: str, cnaes_map: Dict[str, str]) -> Dict[str, Any]:
    """
    Carrega as estatísticas consolidadas da tabela DashboardStats.
    Retorna dicionário estruturado com métricas gerais e DataFrames
    prontos para renderização em gráficos Altair/Streamlit.
    """
    try:
        with sqlite3.connect(caminho_db) as conn:
            df_stats = pd.read_sql_query("SELECT categoria, chave, valor, rotulo FROM DashboardStats", conn)
    except Exception:
        df_stats = pd.DataFrame()

    if df_stats.empty:
        from sql import inicializar_dados_dashboard
        inicializar_dados_dashboard(caminho_db)
        with sqlite3.connect(caminho_db) as conn:
            df_stats = pd.read_sql_query("SELECT categoria, chave, valor, rotulo FROM DashboardStats", conn)

    # 1. Métricas Gerais
    df_geral = df_stats[df_stats["categoria"] == "geral"]
    metricas = {row["chave"]: row["valor"] for _, row in df_geral.iterrows()}
    
    # 2. Distribuição por UF
    df_uf = df_stats[df_stats["categoria"] == "uf"].copy()
    if not df_uf.empty:
        df_uf["Estabelecimentos"] = df_uf["valor"].astype(int)
        df_uf["UF"] = df_uf["chave"]
        df_uf["Estado"] = df_uf["rotulo"]
        total_estab = metricas.get("total_estabelecimentos", df_uf["Estabelecimentos"].sum()) or 1
        df_uf["Porcentagem"] = (df_uf["Estabelecimentos"] / total_estab) * 100
        df_uf.sort_values(by="Estabelecimentos", ascending=False, inplace=True)

    # 3. Distribuição por Situação Cadastral
    df_sit = df_stats[df_stats["categoria"] == "situacao"].copy()
    if not df_sit.empty:
        df_sit["Estabelecimentos"] = df_sit["valor"].astype(int)
        df_sit["Situação"] = df_sit["rotulo"]
        total_sit = df_sit["Estabelecimentos"].sum()
        df_sit["Porcentagem"] = (df_sit["Estabelecimentos"] / total_sit) * 100
        df_sit.sort_values(by="Estabelecimentos", ascending=False, inplace=True)

    # 4. Distribuição por Porte
    df_porte = df_stats[df_stats["categoria"] == "porte"].copy()
    if not df_porte.empty:
        df_porte["Empresas"] = df_porte["valor"].astype(int)
        df_porte["Porte"] = df_porte["rotulo"]
        total_porte = df_porte["Empresas"].sum()
        df_porte["Porcentagem"] = (df_porte["Empresas"] / total_porte) * 100
        df_porte.sort_values(by="Empresas", ascending=False, inplace=True)

    # 5. Top CNAEs
    df_cnae = df_stats[df_stats["categoria"] == "cnae"].copy()
    if not df_cnae.empty:
        df_cnae["Estabelecimentos"] = df_cnae["valor"].astype(int)
        df_cnae["Código"] = df_cnae["chave"]
        
        def traduzir_cnae(c):
            c_str = str(c).strip().zfill(7)
            desc = cnaes_map.get(c_str)
            if not desc:
                # Busca do rótulo padrão na linha
                sub = df_cnae.loc[df_cnae['chave'] == c, 'rotulo']
                desc = sub.values[0] if len(sub) > 0 else "Atividade Comercial"
            c_fmt = f"{c_str[:4]}-{c_str[4]}/{c_str[5:7]}" if len(c_str) == 7 else c_str
            return f"{c_fmt} — {desc}"

        df_cnae["Atividade Econômica"] = df_cnae["chave"].apply(traduzir_cnae)
        df_cnae.sort_values(by="Estabelecimentos", ascending=True, inplace=True)

    return {
        "metricas": metricas,
        "df_uf": df_uf,
        "df_situacao": df_sit,
        "df_porte": df_porte,
        "df_cnae": df_cnae
    }


