import requests
from xml.etree import ElementTree as ET
import zipfile
import pandas as pd

URL_WEBDAV = "https://arquivos.receitafederal.gov.br/public.php/dav/files"
TOKEN = "YggdBLfdninEJX9"

def buscar_arquivos(data: str) -> list[dict]:
    print("Buscando lista de arquivos")

    url = f"{URL_WEBDAV}/{TOKEN}/{data}/"

    response = requests.request("PROPFIND", url, headers={"Depth": "1"})
    response.raise_for_status()

    root = ET.fromstring(response.text)
    ns = {"d": "DAV:"}
    arquivos = []

    for item in root.findall("d:response", ns):
        href = item.find("d:href", ns).text
        nome = href.rstrip("/").split("/")[-1]

        # Pula o directory
        if not nome.endswith(".zip"):
            continue

        size_el = item.find(".//d:getcontentlength", ns)
        etag_el = item.find(".//d:getetag", ns)

        arquivos.append({
            "nome": nome,
            "tamanho": int(size_el.text) if size_el is not None else 0,
            "etag": etag_el.text.strip('"') if etag_el is not None else "",
        })

    return arquivos