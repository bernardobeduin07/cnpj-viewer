import requests
from datetime import date
from tqdm import tqdm
from pathlib import Path
import os
import glob

URL = r"https://arquivos.receitafederal.gov.br/public.php/dav/files"
TOKEN = r"YggdBLfdninEJX9"

PASTA_ARQUIVOS = Path("arquivos")

def buscar_data_atual():
    return str(date.today())[:7]

def gerar_nome_local(nome_arquivo: str) -> str:
    # Exemplo: Empresas0 -> Empresas0_2026-08.zip
    data_atual = buscar_data_atual()
    return PASTA_ARQUIVOS / f"{nome_arquivo}_{data_atual}.zip"

def gerar_nome_temporario(nome_arquivo: str) -> str:
    return PASTA_ARQUIVOS / f"{nome_arquivo}.tmp"

def gerar_url(nome_arquivo: str) -> str:
    data_atual = buscar_data_atual()
    return f"{URL}/{TOKEN}/{data_atual}/{nome_arquivo}.zip"

def limpar_arquivos_antigos(nome_arquivo: str):
    nome_atual = gerar_nome_local(nome_arquivo)
    for arquivo_antigo in glob.glob(f"{nome_arquivo}_*.zip"):
        if arquivo_antigo != nome_atual:
            os.remove(arquivo_antigo)
            print(f"O arquivo antigo {arquivo_antigo} foi removido")

def baixar_arquivo(nome_arquivo: str):
    PASTA_ARQUIVOS.mkdir(exist_ok=True) # Caso a pasta não exista

    nome_arquivo_local = gerar_nome_local(nome_arquivo)
    nome_arquivo_temporario = gerar_nome_temporario(nome_arquivo)
    url_download = gerar_url(nome_arquivo)

    # Caso o arquivo já exista -> early return
    if Path(nome_arquivo_local).is_file():
        print(f"Arquivo {nome_arquivo} já existe.")
        return

    # Busca a página de download
    response = requests.get(url_download, stream=True)
    response.raise_for_status()

    # Caso a resposta dê ok
    limpar_arquivos_antigos(nome_arquivo)

    tamanho_arquivo = int(response.headers.get('content-length', 0))
    chunk_size = 1024 * 1024 # 1 MB

    try:
        # Cria um arquivo temporário
        with open(nome_arquivo_temporario, "wb") as arquivo:
            print(f"Baixando arquivo: {nome_arquivo}")
            # Barra de download
            with tqdm(total=tamanho_arquivo, unit="B", unit_scale=True, desc=nome_arquivo) as barra_progresso:
                # Atualiza a barra de download
                for chunk in response.iter_content(chunk_size=chunk_size):
                    arquivo.write(chunk)
                    barra_progresso.update(len(chunk))

        # Transforma o arquivo temporário em zip
        os.replace(nome_arquivo_temporario, nome_arquivo_local)

        print("Download concluído")
        print(f"Duração do download: {response.elapsed}")
    except Exception:
        # Caso o download dê erro, apaga o arquivo temporário
        if nome_arquivo_temporario.exists():
            os.remove(nome_arquivo_temporario)
        raise