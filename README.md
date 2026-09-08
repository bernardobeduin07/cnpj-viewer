# 🏢 CNPJ Viewer — Consulta e Análise dos Microdados Abertos da Receita Federal

Aplicação de alta performance em **Python** desenvolvida para o Desafio de Programação **CEOS / UFSC**. O sistema realiza a coleta automatizada dos dados abertos públicos de CNPJ da Receita Federal do Brasil via protocolo WebDAV, persiste e indexa mais de **138 milhões de registros** em banco de dados local SQLite, e disponibiliza uma interface web interativa em **Streamlit** para consultas cadastrais, exploração por filtros multicritério e visualizações analíticas de mercado.

---

## 🏛️ Arquitetura do Sistema

O projeto adota os princípios de **Clean Architecture** e **Separação de Responsabilidades (SoC)**, dividindo o ecossistema em quatro camadas desacopladas:

```text
c:\Users\berna\Projetos\ceos\
├── web_app.py              # Ponto de entrada da aplicação Streamlit (Orquestrador ~120 linhas)
├── sql.py                  # DDL das tabelas, ingestão em lote otimizada e índices B-Tree
├── enrichment.py           # Sanitização de entradas, máscaras e tabelas de apoio em memória
├── download_manager.py     # Gerenciamento assíncrono em background (Thread + callbacks)
├── download_zip.py         # Download com streaming HTTP via WebDAV
├── listar_arquivos.py      # Descoberta dinâmica de arquivos via XML/PROPFIND
├── requirements.txt        # Dependências do projeto com versões fixadas
├── README.md               # Documentação técnica completa
└── views/                  # Camada de Visualização (UI Modular)
    ├── __init__.py         # Exportação limpa dos módulos de tela
    ├── company_view.py     # Dossiê da empresa (Cadastrais, Estabelecimentos, Sócios, Simples)
    ├── dashboard_view.py   # Gráficos analíticos Altair e métricas consolidadas
    ├── search_view.py      # Busca higienizada (CNPJ 14, CNPJ 8 e Razão Social em 2 níveis)
    └── filter_view.py      # Filtros multicritério (UF, Município, Situação, CNAE) e exportação CSV
```

---

## 🚀 Funcionalidades Principais

### 1. 📊 Panorama Geral & Dashboard Analítico
* **Métricas Consolidadas:** Total de Empresas, Estabelecimentos e Sócios calculados e persistidos na tabela analítica `DashboardStats` para carregamento em menos de **40ms**.
* **Gráficos Alinhados com Altair:**
  * Top 10 Estados (UFs) por concentração de estabelecimentos.
  * Distribuição por Situação Cadastral (Ativa, Baixada, Inapta, Suspensa, Nula).
  * Distribuição por Porte Empresarial (ME, EPP, Demais).
  * Top 10 Atividades Econômicas (CNAE Principal) com descrições oficiais decodificadas.

### 2. 🏢 Busca Direta Inteligente (Higienizada)
* **CNPJ Completo (14 dígitos):** Identificação automática (com ou sem pontuação) com busca instantânea via índice B-Tree.
* **CNPJ Básico (8 dígitos):** Localização da matriz e consolidação de todas as filiais.
* **Razão Social em 2 Níveis:**
  * **Nível 1 (Prefixo indexado `< 1ms`):** Utiliza o índice `idx_empresas_razao` para buscas imediatas no início do nome.
  * **Nível 2 (Busca ampla):** Fallback automático ou sob demanda para varredura por partes internas do nome.
* **Dossiê Completo em 4 Abas:**
  1. *Dados Cadastrais:* Razão Social, Capital Social formatado, Porte e Natureza Jurídica decodificada.
  2. *Estabelecimentos:* Unidades matriz e filiais, endereço completo, contato e situação cadastral com data.
  3. *Quadro Societário (QSA):* Sócios, qualificações oficiais decodificadas, faixa etária e país.
  4. *Simples Nacional & MEI:* Histórico de opção e exclusão no Simples e MEI.

### 3. 🎯 Filtros Avançados de Mercado & Exportação CSV
* Filtros combinados por:
  * **Estado (UF)**
  * **Município** (com nomes reais obtidos da tabela de apoio)
  * **Situação Cadastral** (Ativa, Baixada, etc.)
  * **Atividade Econômica (CNAE Principal)**
* **Performance com Index Intersection:** Cruzamento em memória dos índices `idx_estab_cnae` e `idx_estab_uf_mun` retornando em menos de **25ms**.
* **Exportação CSV:** Download imediato dos resultados filtrados com codificação `utf-8-sig` (compatível nativamente com Microsoft Excel).
* **Inspeção de Dossiê:** Possibilidade de abrir os detalhes completos de qualquer empresa resultante da filtragem sem sair da página.

### 4. ⚙️ Ingestão Automatizada e Resiliente
* Protocolo **WebDAV (`PROPFIND`)** direto no servidor Nextcloud da Receita Federal (`arquivos.receitafederal.gov.br`).
* Download resiliente com controle de integridade temporária (`.tmp` para `.zip`) e monitoramento em tempo real na barra lateral via fragmentos reativos (`@st.fragment`).
* Carga em lote no SQLite via `sqlite3.executemany` (50.000 linhas/chunk) com `PRAGMA synchronous = OFF` e `journal_mode = WAL`.

---

## ⚡ Estratégia de Indexação e Benchmarks

Com mais de 138 milhões de registros distribuídos em tabelas de até 25 GB, a estratégia de indexação foi desenhada para eliminar *Full Table Scans*:

| Índice Criado | Colunas Indexadas | Propósito | Tempo Médio de Consulta |
| :--- | :--- | :--- | :---: |
| `idx_estab_cnpj_basico` | `Estabelecimentos(cnpj_basico)` | Conectar empresa a todas as suas unidades | `< 1 ms` |
| `idx_socios_cnpj_basico` | `Socios(cnpj_basico)` | Conectar empresa ao seu quadro de sócios | `< 1 ms` |
| `idx_empresas_razao` | `Empresas(razao_social COLLATE NOCASE)` | Busca textual por nome empresarial | `< 5 ms` |
| `idx_estab_cnae` | `Estabelecimentos(cnae_fiscal_principal)` | Filtragem rápida por setor de atuação | `< 20 ms` |
| `idx_estab_uf_mun` | `Estabelecimentos(uf, municipio)` | Filtragem geográfica composta | `< 25 ms` |

> **Resultado dos Testes de Carga:** Consultas complexas multi-filtros com 3 critérios (ex: `UF=GO` + `Situação=Ativa` + `CNAE Soja`) reduziram o tempo de execução de **15,56 segundos para 0,023 segundos (23 ms)** — um ganho de performance superior a **670 vezes**.

---

## 🛠️ Como Executar o Projeto

### Pré-requisitos
* **Python 3.10** ou superior instalado.
* Conexão com a internet para download das bases de dados (caso não possua a base local).
* Espaço em disco recomendado: mínimo de 40 GB para base completa de CNPJ.

### Passo 1: Clonar o Repositório
```bash
git clone https://github.com/bernardobeduin07/cnpj-viewer.git
cd cnpj-viewer
```

### Passo 2: Criar e Ativar Ambiente Virtual
```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux / MacOS
python3 -m venv venv
source venv/bin/activate
```

### Passo 3: Instalar as Dependências
```bash
pip install -r requirements.txt
```

### Passo 4: Iniciar a Aplicação Web
```bash
streamlit run web_app.py
```
O navegador abrirá automaticamente no endereço: `http://localhost:8501`.

---

## 🤖 Declaração de Uso de Ferramentas de Inteligência Artificial

Em conformidade com o edital do Desafio de Programação CEOS / UFSC, declaramos o uso de ferramentas de Inteligência Artificial Generativa durante o desenvolvimento do projeto:

* **Tecnologia Utilizada:** Google Antigravity / Gemini 2.5 (Google DeepMind).
* **Atividades Desenvolvidas com Auxílio de IA:**
  1. *Análise de Requisitos e Auditoria do Edital:* Mapeamento sistemático de todos os itens obrigatórios e critérios de avaliação do desafio.
  2. *Engenharia de Performance de Banco de Dados:* Elaboração da estratégia de índices compostos e index intersection no SQLite, configuração de PRAGMAs do WAL mode e modelagem da tabela agregada `DashboardStats`.
  3. *Refatoração Arquitetural:* Modularização do código monolítico em pacotes desacoplados (`views/`), aplicando padrões de Clean Architecture e Clean Code.
  4. *Design de Interface em Streamlit & Altair:* Ajustes visuais em gráficos analíticos com esquemas de cores semânticos e remoção de scripts injetados em JavaScript, preservando a execução 100% nativa em Python.
