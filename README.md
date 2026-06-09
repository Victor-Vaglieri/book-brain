# Leitor de PDF Inteligente (RAG Local)

Este repositório contém a infraestrutura e o código-fonte de uma aplicação desktop focada em transformar a leitura de arquivos PDF em uma experiência assistida por Inteligência Artificial rodando localmente.

## 1. Visão Geral

O **Leitor de PDF Inteligente** atua como um assistente de estudo e análise de documentos onde o processamento de linguagem natural e a recuperação de informação são tratados localmente, garantindo privacidade e eficiência.

### Objetivos do Projeto
1.  **Privacidade Total:** Inferência de IA e armazenamento vetorial executados na máquina local (sem chamadas a APIs de terceiros).
2.  **Persistência Resiliente:** Gestão do banco de dados vetorial via ChromaDB, garantindo que o conhecimento de PDFs lidos anteriormente sobreviva ao reinício da aplicação.
3.  **Processamento Assíncrono:** Extração de texto e geração de embeddings feitas em segundo plano para não congelar a interface de usuário (UI).
4.  **Interface Dinâmica:** Leitor de PDF com biblioteca nativa, suporte avançado a zoom, modo escuro e interface de chat inspirada em apps de mensagens.

### 2.1 Interface e Navegação (PyQt6 + PyMuPDF)
O sistema realiza a leitura fluida dos documentos PDF com recursos de Zoom via `Ctrl + Scroll` e navegação de páginas através de atalhos de teclado e de campos editáveis. A área de visualização possui suporte nativo a "Modo Escuro" com inversão de pixels dinâmicos para conforto visual.

> **📷 Instrução de Print:** Tire um print com o aplicativo aberto lendo uma página do livro "TDD - Desenvolvimento Guiado por Testes - Autor (Kent Beck)". O Zoom deve estar aplicado e a checkbox "Modo Escuro" ativada (mostrando o fundo preto).

<img width="800" alt="Interface de Leitura e Modo Escuro" src="COLE_O_LINK_DO_GITHUB_AQUI" />

*Demonstração do Leitor de PDF processando o livro TDD de Kent Beck, com inversão dinâmica de pixels ativada.*

### 2.2 Persistência de Dados (ChromaDB + JSON)
A resiliência de dados é garantida pelo uso do `chromadb.PersistentClient` associado a um arquivo de estado local `library.json`. O progresso de leitura, metadados dos livros abertos (capas geradas via hash) e vetores indexados são mantidos de forma robusta entre ciclos de vida da aplicação.

> **📷 Instrução de Print:** Tire um print da tela inicial "Sua Biblioteca" mostrando o Card gerado para o livro TDD. Deve ficar visível a miniatura da capa do livro extraída automaticamente e a porcentagem de leitura salva abaixo dela.

<img width="800" alt="Grade de Biblioteca e Persistência" src="COLE_O_LINK_DO_GITHUB_AQUI" />

*Evidência da persistência de metadados: Geração de miniatura da capa e estado de leitura (porcentagem lida) salvos localmente.*

### 2.3 Recuperação Aumentada por Geração (RAG)
A aplicação implementa um pipeline RAG inteligente. Ao realizar uma pergunta no chat, a engine de embeddings busca os três blocos de texto mais similares da biblioteca (ou restritos estritamente ao documento em leitura) e anexa como contexto na memória da LLM, reduzindo consideravelmente a alucinação de dados.

> **📷 Instrução de Print:** Na tela de leitura do TDD, faça uma pergunta focada no livro pelo Chat (ex: "Qual a diferença entre refatoração e escrever código no ciclo Red-Green?"). Tire o print focando nos balões de texto: a sua mensagem alinhada à direita, e a Llama 3.2 respondendo com a etiqueta "(Contexto: TDD)" alinhada à esquerda.

<img width="800" alt="Integração RAG e Inferência Llama 3.2" src="COLE_O_LINK_DO_GITHUB_AQUI" />

*Pipeline RAG em ação: LLM respondendo com base no contexto injetado do documento "TDD", utilizando layout de balões de mensagens.*


## 3. Fluxo de Arquitetura

1.  **Ingestão:** O **PyMuPDF** carrega o PDF e extrai o texto a cada transição de página feita pelo usuário.
2.  **Processamento Background:** Uma **QThread** assíncrona absorve o texto, fatia em pequenos chunks (fragmentos) e gera vetores multidimensionais (embeddings).
3.  **Armazenamento Vetorial:** O **ChromaDB** gerencia de forma otimizada os embeddings em persistência de disco.
4.  **Recuperação Semântica:** A pergunta enviada no chat aciona o banco vetorial buscando semânticas que respondam à dúvida atual.
5.  **Inferência e IA:** O contexto enriquecido é submetido via REST API ao Ollama, que devolve a resposta final em formato HTML para a interface gráfica.

## 4. Tecnologias e Ferramentas (Stack)

*   **Interface Gráfica (GUI):** PyQt6
*   **Processamento de PDF:** PyMuPDF (`fitz`)
*   **Embeddings de Linguagem:** `sentence-transformers` (Modelo Leve: `all-MiniLM-L6-v2`)
*   **Banco de Dados Vetorial:** ChromaDB (Persistente Local)
*   **Motor de Inteligência Artificial:** Ollama executando localmente o modelo `llama3.2`

## 5. Estrutura do Projeto

```text
projeto/
├── covers/               # Diretório (gerado dinamicamente) com miniaturas extraídas das capas
├── chroma_db/            # Banco de dados vetorial gerenciado pelo ChromaDB
├── venv_rag/             # Virtual Environment isolado contendo as libs (Git ignored)
├── main.py               # Front-end da aplicação, GUI e Threads de Ingestão e Chat
├── rag.py                # Back-end da abstração do pipeline RAG (Embedder e DB)
├── library.json          # Estado JSON rastreando metadados de leitura (pág, capas)
├── GEMINI.md             # Documentação de tracking para futuras manutenções com LLMs
└── README.md             # Este documento técnico
```

## 6. Execução

### Passo a Passo

1.  **Pré-requisitos de IA:**
    *   Ter o [Ollama](https://ollama.com/) instalado no Windows.
    *   Fazer o download prévio do modelo abrindo um terminal e rodando:
    ```powershell
    ollama run llama3.2
    ```

2. **Preparação do Ambiente Python:** 
    ```powershell
    # Criar e ativar o ambiente virtual (Recomendado: Python 3.12)
    py -3.12 -m venv venv_rag
    .\venv_rag\Scripts\activate

    # Instalar a Stack tecnológica requerida
    pip install PyQt6 PyMuPDF sentence-transformers chromadb requests
    ```

3.  **Iniciando a Plataforma:**
    ```powershell
    # Rodar o código principal via Python dentro do venv ativado
    python main.py
    ```

