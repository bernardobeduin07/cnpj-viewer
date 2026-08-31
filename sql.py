import sqlite3
from sqlalchemy import create_engine
import zipfile
import pandas as pd
from pathlib import Path
from tqdm import tqdm

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

    print("Tabelas verificadas")

def inserir_arquivo_no_banco_dados(nome_arquivo: str):
    print(f"Inserindo arquivo {nome_arquivo} no banco de dados")
    caminho_arquivo = gerar_nome_local(nome_arquivo)

    with zipfile.ZipFile(caminho_arquivo, 'r') as zip:
        nome_csv = zip.namelist()[0]
        tamanho_csv = zip.getinfo(nome_csv).file_size
        
        with zip.open(nome_csv) as arquivo:
            nome_tabela = nome_arquivo.rstrip("0123456789")
            colunas = COLUNAS_TABELAS[nome_tabela]
            
            df = pd.read_csv(
                arquivo, 
                sep=';', 
                header=None, 
                names=colunas, 
                encoding='latin1',
                dtype=str,
                chunksize=1000
            )

            engine = create_engine(f"sqlite:///{NOME_DB}")

            # Barra de progresso
            with tqdm(total=tamanho_csv, unit="B", unit_scale=True, desc=nome_tabela) as barra:
                for df_chunk in df:
                    df_chunk.to_sql(nome_tabela, con=engine, if_exists="append", index=False)
                    bytes_lidos = arquivo.tell()
                    barra.update(bytes_lidos - barra.n)

    print("Arquivos inseridos com sucesso")