import sqlite3
import zipfile
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from datetime import datetime

from download_zip import gerar_nome_local

NOME_DB = "database_cnpj.db"
COLUNAS_TABELAS = {
    "Cnaes": [
        "codigo",
        "descricao"
    ],
    "Empresas": [
        "cnpj_basico", 
        "razao_social", 
        "natureza_juridica", 
        "qualificacao_responsavel", 
        "capital_social", 
        "porte_empresa", 
        "ente_federativo_responsavel"
    ],
    "Estabelecimentos": [
        "cnpj_basico",
        "cnpj_ordem",
        "cnpj_dv",
        "identificador_matriz",
        "nome_fantasia",
        "situacao_cadastral",
        "data_situacao_cadastral" ,
        "motivo_situacao_cadastral",
        "nome_cidade_exterior",
        "codigo_pais",
        "data_inicio_atividade",
        "cnae_fiscal_principal",
        "cnae_fiscal_secundario",
        "tipo_logradouro",
        "logradouro",
        "numero",
        "complemento",
        "bairro",
        "cep",
        "uf",
        "municipio",
        "ddd_1",
        "telefone_1",
        "ddd_2",
        "telefone_2",
        "ddd_fax",
        "fax",
        "correio_eletronico",
        "situacao_especial",
        "data_situacao_especial"
    ],
    "Motivos": [
        "codigo",
        "descricao"
    ],
    "Municipios": [
        "codigo",
        "descricao"
    ],
    "Naturezas": [
        "codigo",
        "descricao"
    ],
    "Paises": [
        "codigo",
        "descricao"
    ],
    "Qualificacoes": [
        "codigo",
        "descricao"
    ],
    "Simples": [
        "cnpj_basico",
        "opcao_simples",
        "data_opcao_simples",
        "data_exclusao_simples",
        "opcao_mei",
        "data_opcao_mei",
        "data_exclusao_mei"
    ],
    "Socios": [
        "cnpj_basico",
        "identificador_socio",
        "nome_socio",
        "cnpj_cpf_socio",
        "qualificacao_socio",
        "data_entrada_sociedade",
        "pais",
        "representante_legal",
        "nome_representante",
        "qualificacao_representante",
        "faixa_etaria"
    ]
}

def verificar_tabelas():
    print("Verificando tabelas")

    with sqlite3.connect(NOME_DB) as cursor:

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ControleCargas (
                nome_arquivo TEXT PRIMARY KEY,
                data_carga TEXT,
                linhas_inseridas INT,
                status TEXT -- 'CONCLUIDO', 'EM_ANDAMENTO', 'ERRO'
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Cnaes (
                codigo TEXT UNIQUE,
                descricao TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Empresas (
                cnpj_basico TEXT UNIQUE,
                razao_social TEXT,
                natureza_juridica TEXT, 
                qualificacao_responsavel TEXT, 
                capital_social TEXT, 
                porte_empresa TEXT, 
                ente_federativo_responsavel TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Estabelecimentos (
                cnpj_basico TEXT,
                cnpj_ordem TEXT,
                cnpj_dv TEXT,
                identificador_matriz TEXT,
                nome_fantasia TEXT,
                situacao_cadastral TEXT,
                data_situacao_cadastral TEXT,
                motivo_situacao_cadastral TEXT,
                nome_cidade_exterior TEXT,
                codigo_pais TEXT,
                data_inicio_atividade TEXT,
                cnae_fiscal_principal TEXT,
                cnae_fiscal_secundario TEXT,
                tipo_logradouro TEXT,
                logradouro TEXT,
                numero TEXT,
                complemento TEXT,
                bairro TEXT,
                cep TEXT,
                uf TEXT,
                municipio TEXT,
                ddd_1 TEXT,
                telefone_1 TEXT,
                ddd_2 TEXT,
                telefone_2 TEXT,
                ddd_fax TEXT,
                fax TEXT,
                correio_eletronico TEXT,
                situacao_especial TEXT,
                data_situacao_especial TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Motivos (
                codigo TEXT UNIQUE,
                descricao TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Municipios (
                codigo TEXT UNIQUE,
                descricao TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Naturezas (
                codigo TEXT UNIQUE,
                descricao TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Paises (
                codigo TEXT UNIQUE,
                descricao TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Qualificacoes (
                codigo TEXT UNIQUE,
                descricao TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Simples (
                cnpj_basico TEXT UNIQUE,
                opcao_simples TEXT,
                data_opcao_simples TEXT,
                data_exclusao_simples TEXT,
                opcao_mei TEXT,
                data_opcao_mei TEXT,
                data_exclusao_mei TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Socios (
                cnpj_basico TEXT,
                identificador_socio TEXT,
                nome_socio TEXT,
                cnpj_cpf_socio TEXT,
                qualificacao_socio TEXT,
                data_entrada_sociedade TEXT,
                pais TEXT,
                representante_legal TEXT,
                nome_representante TEXT,
                qualificacao_representante TEXT,
                faixa_etaria TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS DashboardStats (
                categoria TEXT,
                chave TEXT,
                valor REAL,
                rotulo TEXT,
                PRIMARY KEY (categoria, chave)
            )
        """)

    print("Tabelas verificadas")

DADOS_CONSOLIDADOS_INICIAIS = [
    # Métricas Gerais
    ("geral", "total_empresas", 37137354, "Total de Empresas"),
    ("geral", "total_estabelecimentos", 72789638, "Total de Estabelecimentos"),
    ("geral", "total_socios", 28146721, "Total de Sócios Registrados"),
    ("geral", "total_ativas", 28148920, "Estabelecimentos Ativos"),
    ("geral", "taxa_ativas", 38.67, "Taxa de Atividade (%)"),

    # Distribuição por Situação Cadastral
    ("situacao", "02", 28148920, "02 — ATIVA"),
    ("situacao", "08", 34286153, "08 — BAIXADA"),
    ("situacao", "04", 9926527, "04 — INAPTA"),
    ("situacao", "03", 318161, "03 — SUSPENSA"),
    ("situacao", "01", 109877, "01 — NULA"),

    # Top 10 Estados (UFs)
    ("uf", "SP", 21057307, "São Paulo"),
    ("uf", "MG", 7887626, "Minas Gerais"),
    ("uf", "RJ", 6168705, "Rio de Janeiro"),
    ("uf", "RS", 4958524, "Rio Grande do Sul"),
    ("uf", "PR", 4956430, "Paraná"),
    ("uf", "BA", 3592816, "Bahia"),
    ("uf", "SC", 3547774, "Santa Catarina"),
    ("uf", "GO", 2634565, "Goiás"),
    ("uf", "PE", 2174559, "Pernambuco"),
    ("uf", "CE", 2063941, "Ceará"),

    # Distribuição por Porte
    ("porte", "01", 27436228, "Microempresa (ME)"),
    ("porte", "05", 8480046, "Demais (Grande / Médio Porte)"),
    ("porte", "03", 1217633, "Empresa de Pequeno Porte (EPP)"),

    # Top 10 CNAEs
    ("cnae", "4781400", 3712955, "Comércio varejista de artigos do vestuário e acessórios"),
    ("cnae", "9492800", 3316652, "Atividades de organizações políticas"),
    ("cnae", "5611203", 2040705, "Lanchonetes, casas de chá, de sucos e similares"),
    ("cnae", "9602501", 2015072, "Cabeleireiros, manicure e pedicure"),
    ("cnae", "7319002", 1833534, "Promoção de vendas"),
    ("cnae", "8888888", 1806750, "Atividade econômica não informada"),
    ("cnae", "4712100", 1727231, "Minimercados, mercearias e armazéns"),
    ("cnae", "4399103", 1388849, "Obras de alvenaria"),
    ("cnae", "5611201", 1271343, "Restaurantes e similares"),
    ("cnae", "8219999", 1238355, "Preparação de documentos e serviços de apoio administrativo")
]

def inicializar_dados_dashboard(caminho_db=NOME_DB):
    """Garante a existência e o preenchimento inicial da tabela DashboardStats."""
    with sqlite3.connect(caminho_db) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS DashboardStats (
                categoria TEXT,
                chave TEXT,
                valor REAL,
                rotulo TEXT,
                PRIMARY KEY (categoria, chave)
            )
        """)
        # Verifica se já possui dados
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM DashboardStats")
        if cur.fetchone()[0] == 0:
            conn.executemany(
                "INSERT OR REPLACE INTO DashboardStats (categoria, chave, valor, rotulo) VALUES (?, ?, ?, ?)",
                DADOS_CONSOLIDADOS_INICIAIS
            )
            conn.commit()
            print("Tabela DashboardStats inicializada com estatísticas consolidadas.")

def atualizar_estatisticas_dashboard(caminho_db=NOME_DB):
    """Recalcula todas as estatísticas consolidadas diretamente da base."""
    with sqlite3.connect(caminho_db) as conn:
        cur = conn.cursor()
        print("Recalculando estatísticas gerais...")
        
        # 1. Totais
        cur.execute("SELECT COUNT(*) FROM Empresas")
        tot_emp = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM Estabelecimentos")
        tot_estab = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM Socios")
        tot_soc = cur.fetchone()[0]
        
        # 2. Situações
        cur.execute("SELECT situacao_cadastral, COUNT(*) FROM Estabelecimentos GROUP BY situacao_cadastral")
        rows_sit = cur.fetchall()
        tot_ativas = sum(qtd for sit, qtd in rows_sit if str(sit) == "02")
        taxa_ativas = (tot_ativas / tot_estab * 100) if tot_estab > 0 else 0

        registros = [
            ("geral", "total_empresas", tot_emp, "Total de Empresas"),
            ("geral", "total_estabelecimentos", tot_estab, "Total de Estabelecimentos"),
            ("geral", "total_socios", tot_soc, "Total de Sócios Registrados"),
            ("geral", "total_ativas", tot_ativas, "Estabelecimentos Ativos"),
            ("geral", "taxa_ativas", round(taxa_ativas, 2), "Taxa de Atividade (%)")
        ]

        rotulos_sit = {
            "01": "01 — NULA",
            "02": "02 — ATIVA",
            "03": "03 — SUSPENSA",
            "04": "04 — INAPTA",
            "08": "08 — BAIXADA"
        }
        for sit, qtd in rows_sit:
            if sit:
                registros.append(("situacao", str(sit), qtd, rotulos_sit.get(str(sit), f"Situação {sit}")))

        # 3. Top 10 UFs
        cur.execute("SELECT uf, COUNT(*) as qtd FROM Estabelecimentos GROUP BY uf ORDER BY qtd DESC LIMIT 10")
        for uf, qtd in cur.fetchall():
            if uf:
                registros.append(("uf", str(uf), qtd, str(uf)))

        # 4. Porte
        cur.execute("SELECT porte_empresa, COUNT(*) FROM Empresas GROUP BY porte_empresa")
        rotulos_porte = {
            "01": "Microempresa (ME)",
            "03": "Empresa de Pequeno Porte (EPP)",
            "05": "Demais (Grande / Médio Porte)"
        }
        for p, qtd in cur.fetchall():
            if p:
                registros.append(("porte", str(p), qtd, rotulos_porte.get(str(p), f"Porte {p}")))

        # 5. Top 10 CNAEs
        cur.execute("SELECT cnae_fiscal_principal, COUNT(*) as qtd FROM Estabelecimentos GROUP BY cnae_fiscal_principal ORDER BY qtd DESC LIMIT 10")
        for cnae, qtd in cur.fetchall():
            if cnae:
                registros.append(("cnae", str(cnae), qtd, str(cnae)))

        # Limpa e reinsere
        conn.execute("DELETE FROM DashboardStats")
        conn.executemany(
            "INSERT OR REPLACE INTO DashboardStats (categoria, chave, valor, rotulo) VALUES (?, ?, ?, ?)",
            registros
        )
        conn.commit()
        print("Estatísticas recalculadas e salvas com sucesso!")

def criar_indices():
    """Executa apenas após a carga completa dos dados."""

    print("Criando índices essenciais...")

    with sqlite3.connect(NOME_DB) as conn:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_estab_cnpj_basico ON Estabelecimentos (cnpj_basico);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_socios_cnpj_basico ON Socios (cnpj_basico);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_empresas_razao ON Empresas (razao_social COLLATE NOCASE);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_estab_cnae ON Estabelecimentos (cnae_fiscal_principal);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_estab_uf_mun ON Estabelecimentos (uf, municipio);")
        conn.execute("ANALYZE;")

        print("Índices criados com sucesso!")

def arquivo_ja_inserido_no_banco(nome_arquivo_zip: str) -> bool:
    """
    Verifica se o arquivo específico já consta como 'CONCLUIDO' na tabela de controle.
    """
    with sqlite3.connect(NOME_DB) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM ControleCargas WHERE nome_arquivo = ? AND status = 'CONCLUIDO'",
            (nome_arquivo_zip,)
        )
        return cur.fetchone() is not None

def inserir_arquivo_no_banco_dados(nome_arquivo: str, callback=None):
    print(f"\n🚀 Inserindo {nome_arquivo} no banco de dados...")
    caminho_arquivo = gerar_nome_local(nome_arquivo)

    if not caminho_arquivo.is_file():
        print(f"❌ Arquivo {caminho_arquivo} não encontrado!")
        return

    # Registra início da carga como EM_ANDAMENTO
    with sqlite3.connect(NOME_DB) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO ControleCargas (nome_arquivo, data_carga, status)
            VALUES (?, ?, 'EM_ANDAMENTO')
        """, (caminho_arquivo.name, datetime.now().isoformat()))

    with zipfile.ZipFile(caminho_arquivo, 'r') as zip_ref:
        nome_csv = zip_ref.namelist()[0]
        tamanho_csv = zip_ref.getinfo(nome_csv).file_size

        nome_tabela = nome_arquivo.rstrip("0123456789")
        colunas = COLUNAS_TABELAS[nome_tabela]
        placeholders = ",".join(["?"] * len(colunas))
        sql_insert = f"INSERT OR IGNORE INTO {nome_tabela} VALUES ({placeholders})"

        total_linhas = 0

        # Conexão direta com SQLite otimizada
        with sqlite3.connect(NOME_DB) as conn:
            cursor = conn.cursor()

            # 🔥 PRAGMAs mágicos para máxima velocidade de escrita:
            cursor.execute("PRAGMA synchronous = OFF;")
            cursor.execute("PRAGMA journal_mode = WAL;")
            cursor.execute("PRAGMA cache_size = -128000;") # 128 MB de cache RAM
            cursor.execute("PRAGMA temp_store = MEMORY;")

            with zip_ref.open(nome_csv) as arquivo:
                # Chunk de 50.000 em vez de 1.000
                df_iter = pd.read_csv(
                    arquivo,
                    sep=';',
                    header=None,
                    names=colunas,
                    encoding='latin1',
                    dtype=str,
                    chunksize=50_000
                )

                with tqdm(total=tamanho_csv, unit="B", unit_scale=True, desc=f"Carregando {nome_arquivo}") as barra:
                    for df_chunk in df_iter:
                        # Substitui NaNs por None (NULL no SQL)
                        df_chunk = df_chunk.where(pd.notnull(df_chunk), None)

                        # Insere nativamente em lote de tuplas (ultrarrápido)
                        cursor.executemany(sql_insert, df_chunk.itertuples(index=False, name=None))
                        
                        total_linhas += len(df_chunk)
                        bytes_lidos = arquivo.tell()
                        barra.update(bytes_lidos - barra.n)

                        if callback:
                            callback(bytes_lidos, tamanho_csv)

            # Commita a transação no final do arquivo
            conn.commit()

            # Restaura PRAGMA padrão
            cursor.execute("PRAGMA synchronous = NORMAL;")

    # Atualiza status final com o total exato de linhas inseridas
    with sqlite3.connect(NOME_DB) as conn:
        conn.execute("""
            UPDATE ControleCargas 
            SET status = 'CONCLUIDO', data_carga = ?, linhas_inseridas = ?
            WHERE nome_arquivo = ?
        """, (datetime.now().isoformat(), total_linhas, caminho_arquivo.name))

    print(f"{nome_arquivo} concluido com sucesso! ({total_linhas:,} linhas inseridas)")