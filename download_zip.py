import os
import re
from pathlib import Path
from datetime import date
from xml.etree import ElementTree as ET
import requests
from tqdm import tqdm

URL_BASE = r"https://arquivos.receitafederal.gov.br/public.php/dav/files"
TOKEN = r"YggdBLfdninEJX9"

PASTA_ARQUIVOS = Path("arquivos")

def obter_data_mais_recente() -> str:
    """
    Descobre dinamicamente a pasta mais recente disponível no WebDAV da Receita Federal.
    Se a requisição falhar, faz fallback para a data dos arquivos já existentes em 'arquivos/'.
    """
    url_raiz = f"{URL_BASE}/{TOKEN}/"

    try:
        response = requests.request("PROPFIND", url_raiz, headers={"Depth": "1"}, timeout=10)
        if response.status_code in (200, 207):
            root = ET.fromstring(response.text)
            name_spaces = {"d": "DAV:"}
            datas = []

            for item in root.findall("d:response", name_spaces):
                href = item.find("d:href", name_spaces).text.rstrip("/")
                nome_pasta = href.split("/")[-1]
                # Valida se o formato é YYYY-MM (ex: 2026-08)
                if re.match(r"^\d{4}-\d{2}$", nome_pasta):
                    datas.append(nome_pasta)

            if datas:
                return sorted(datas)[-1]  # Retorna a data mais recente
            
    except Exception as e:
        print(f"Aviso: Não foi possível obter data via WebDAV ({e}). Usando fallback local.")
    # Fallback 1: Verifica os arquivos locais já baixados na pasta 'arquivos/'
    if PASTA_ARQUIVOS.exists():
        zips = list(PASTA_ARQUIVOS.glob("*_*.zip"))
        if zips:
            datas_locais = set()
            for z in zips:
                match = re.search(r"(\d{4}-\d{2})\.zip$", z.name)
                if match:
                    datas_locais.add(match.group(1))
            if datas_locais:
                return sorted(datas_locais)[-1]
    # Fallback 2: Data atual caso nada exista
    return str(date.today())[:7]

def gerar_nome_local(nome_arquivo: str, data: str | None = None) -> Path:
    if data is None:
        data = obter_data_mais_recente()
    return PASTA_ARQUIVOS / f"{nome_arquivo}_{data}.zip"

def gerar_nome_temporario(nome_arquivo: str) -> Path:
    return PASTA_ARQUIVOS / f"{nome_arquivo}.tmp"
    
def gerar_url(nome_arquivo: str, data: str | None = None) -> str:
    if data is None:
        data = obter_data_mais_recente()
    return f"{URL_BASE}/{TOKEN}/{data}/{nome_arquivo}.zip"

def limpar_arquivos_antigos(nome_arquivo: str, data_atual: str):
    nome_atual = gerar_nome_local(nome_arquivo, data_atual)
    for arquivo_antigo in PASTA_ARQUIVOS.glob(f"{nome_arquivo}_*.zip"):
        if arquivo_antigo.resolve() != nome_atual.resolve():
            try:
                arquivo_antigo.unlink()
                # Remove também o marcador .done do arquivo antigo se houver
                marcador_antigo = arquivo_antigo.with_suffix(".done")
                if marcador_antigo.exists():
                    marcador_antigo.unlink()
                print(f"O arquivo antigo {arquivo_antigo.name} foi removido.")
            except Exception as erro:
                print(f"Erro ao remover arquivo antigo {arquivo_antigo}: {erro}")

def baixar_arquivo(nome_arquivo: str, callback=None, data: str | None = None) -> Path:
    PASTA_ARQUIVOS.mkdir(exist_ok=True)

    if data is None:
        data = obter_data_mais_recente()

    nome_arquivo_local = gerar_nome_local(nome_arquivo, data)
    nome_arquivo_temporario = gerar_nome_temporario(nome_arquivo)
    url_download = gerar_url(nome_arquivo, data)

    # Se o arquivo zip da data já existe localmente, pula o download
    if nome_arquivo_local.is_file():
        print(f"Arquivo {nome_arquivo_local.name} já existe localmente.")
        return nome_arquivo_local
    
    print(f"Iniciando download de {url_download}...")

    response = requests.get(url_download, stream=True, timeout=30)
    response.raise_for_status()

    # Limpa versões anteriores apenas após a confirmação de que a nova versão existe na URL
    limpar_arquivos_antigos(nome_arquivo, data)
    tamanho_total = int(response.headers.get("content-length", 0))
    chunk_size = 1024 * 1024  # 1 MB
    
    try:
        with open(nome_arquivo_temporario, "wb") as f:
            with tqdm(total=tamanho_total, unit="B", unit_scale=True, desc=nome_arquivo) as barra:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if not chunk:
                        continue
                    f.write(chunk)
                    barra.update(len(chunk))
                    if callback:
                        callback(f.tell(), tamanho_total)

        # Renomeia com sucesso o temporário para o destino final
        os.replace(nome_arquivo_temporario, nome_arquivo_local)
        print(f"Download de {nome_arquivo_local.name} concluído com sucesso!")
        return nome_arquivo_local
    
    except Exception:
        if nome_arquivo_temporario.exists():
            nome_arquivo_temporario.unlink()
        raise