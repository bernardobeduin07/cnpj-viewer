import threading
import time
from typing import List, Dict

import streamlit as st

from download_zip import baixar_arquivo, obter_data_mais_recente, PASTA_ARQUIVOS
from listar_arquivos import buscar_arquivos
from sql import inserir_arquivo_no_banco_dados, verificar_tabelas, arquivo_ja_inserido_no_banco, criar_indices


class DownloadManager:
    """Gerenciador de downloads e importações em segundo plano."""

    def __init__(self):
        self.em_execucao: bool = False
        self.verificando_api: bool = False
        self.arquivo_atual: str = ""
        self.etapa_atual: str = ""  # "Baixando" ou "Importando"
        
        self.total_arquivos: int = 0
        self.concluidos: int = 0
        
        self.arquivo_bytes_lidos: int = 0
        self.arquivo_bytes_total: int = 0
        
        self.historico_logs: List[str] = []
        self.thread: threading.Thread | None = None
        self._cancelar: bool = False
        self._ja_iniciou_auto: bool = False

    def adicionar_log(self, mensagem: str):
        timestamp = time.strftime("%H:%M:%S")
        self.historico_logs.append(f"[{timestamp}] {mensagem}")

    def atualizar_progresso_arquivo(self, lidos: int, total: int):
        self.arquivo_bytes_lidos = lidos
        self.arquivo_bytes_total = total

    def obter_arquivos_pendentes(self, data: str | None = None) -> List[Dict]:
        """Compara os arquivos disponíveis na API com os já salvos e processados (.done) localmente."""
        if data is None:
            data = obter_data_mais_recente()

        PASTA_ARQUIVOS.mkdir(exist_ok=True)
        arquivos_api = buscar_arquivos(data)
        pendentes = []

        for arq in arquivos_api:
            nome_sem_ext = arq["nome"].replace(".zip", "")
            caminho_local = PASTA_ARQUIVOS / f"{nome_sem_ext}_{data}.zip"
            
            # O arquivo é pendente se NÃO existe no disco OU se ainda NÃO foi inserido com sucesso no banco:
            if not caminho_local.is_file() or not arquivo_ja_inserido_no_banco(caminho_local.name):
                pendentes.append(arq)

        return pendentes

    def _executar_tarefa(self, arquivos: List[Dict], importar_banco: bool):
        self.em_execucao = True
        self._cancelar = False
        self.total = len(arquivos)
        self.concluidos = 0
        self.adicionar_log(f"Iniciando processamento de {self.total} arquivo(s)...")

        # Garante que o esquema do banco de dados exista antes de importar
        try:
            verificar_tabelas()
        except Exception as erro:
            self.adicionar_log(f"Aviso na verificação de tabelas: {erro}")

        for item in arquivos:
            if self._cancelar:
                self.adicionar_log("Processamento cancelado pelo usuário.")
                break

            nome_arquivo_local = item["nome"]
            nome_arquivo = nome_arquivo_local.replace(".zip", "")
            
            self.arquivo_atual = nome_arquivo
            self.arquivo_bytes_lidos = 0
            self.arquivo_bytes_total = item["tamanho"]

            # Etapa 1: Download
            self.etapa_atual = "Baixando"
            self.adicionar_log(f"Baixando {nome_arquivo}...")

            try:
                baixar_arquivo(nome_arquivo, callback=self.atualizar_progresso_arquivo)
            except Exception as erro:
                self.adicionar_log(f"Erro no download de {nome_arquivo}: {erro}")
                continue

            # Etapa 2: Importação para o SQLite
            if importar_banco:
                if self._cancelar:
                    break
                self.etapa_atual = "Importando para o banco"
                self.adicionar_log(f"Inserindo {nome_arquivo} no banco SQLite...")
                self.arquivo_bytes_lidos = 0
                self.arquivo_bytes_total = 1 # Sera atualizado no callback pelo zip
                try:
                    inserir_arquivo_no_banco_dados(nome_arquivo, callback=self.atualizar_progresso_arquivo)
                except Exception as erro:
                    self.adicionar_log(f"Erro ao inserir {nome_arquivo} no banco: {erro}")
                    continue

            self.concluidos += 1
            self.adicionar_log(f"{nome_arquivo} processado com sucesso ({self.concluidos}/{self.total})")

        self.em_execucao = False
        self.arquivo_atual = ""
        self.etapa_atual = ""
        self.arquivo_bytes_lidos = 0
        self.arquivo_bytes_total = 0

        if not self._cancelar:
            try:
                self.adicionar_log("Criando e verificando índices essenciais...")
                criar_indices()
            except Exception as e:
                self.adicionar_log(f"Aviso ao indexar banco: {e}")
            self.adicionar_log("🎉 Todos os downloads e importações foram concluídos!")

    def verificar_e_iniciar_automatico(self):
        """Inicia a verificação e o download automaticamente na primeira vez."""
        if self._ja_iniciou_auto or self.em_execucao or self.verificando_api:
            return
            
        self._ja_iniciou_auto = True
        self.verificando_api = True
        
        def tarefa():
            try:
                self.adicionar_log("🔍 Verificando atualizações automaticamente na Receita Federal...")
                pendentes = self.obter_arquivos_pendentes()
                if pendentes:
                    self._executar_tarefa(pendentes, importar_banco=True)
                else:
                    self.adicionar_log("✅ Todos os arquivos já estão baixados e atualizados.")
            except Exception as e:
                self.adicionar_log(f"❌ Erro na verificação automática: {e}")
            finally:
                self.verificando_api = False

        self.thread = threading.Thread(target=tarefa, daemon=True)
        self.thread.start()

    def cancelar(self):
        """Sinaliza para cancelar os próximos downloads."""
        if self.em_execucao:
            self._cancelar = True
            self.adicionar_log("Solicitação de cancelamento enviada...")


@st.cache_resource
def obter_gerenciador() -> DownloadManager:
    """Retorna uma única instância compartilhada do gerenciador de downloads."""
    return DownloadManager()