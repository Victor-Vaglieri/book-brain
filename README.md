# Leitor de PDF Inteligente (RAG Local)

Este repositório contém a infraestrutura e o código-fonte de uma aplicação desktop focada em transformar a leitura de arquivos PDF em uma experiência assistida por Inteligência Artificial rodando localmente.

## 1. Visão Geral

O **Leitor de PDF Inteligente** atua como um assistente de estudo e análise de documentos onde o processamento de linguagem natural e a recuperação de informação são tratados localmente, garantindo maior eficiência.

### Objetivos do Projeto
1.  **Privacidade Total:** Inferência de IA e armazenamento vetorial executados estritamente na máquina local (sem chamadas a APIs de terceiros).
2.  **Persistência Resiliente:** Gestão do banco de dados vetorial via ChromaDB, garantindo que o conhecimento de PDFs lidos anteriormente sobreviva ao reinício da aplicação.
3.  **Processamento Assíncrono e Semântico:** Extração de texto segmentada por blocos lógicos usando divisores semânticos (pontuação, parágrafos), gerados em segundo plano para não congelar a interface de usuário.
4.  **Memória Contextual (Chat History):** O assistente mantém o histórico da conversa, permitindo perguntas conectadas.
5.  **Re-ranqueamento Preciso:** Filtro de anti-alucinação usando modelos Cross-Encoder que analisam a relevância dos blocos encontrados antes de enviá-los para a IA.
6.  **Interface Modular e Responsiva:** Leitor de PDF com biblioteca nativa, grade de exibição responsiva e UI componentizada (separação clara de responsabilidades).

## 2. Resultados e Evidências

Abaixo estão documentadas as evidências que comprovam a implementação dos objetivos do aplicativo.

### 2.1 Interface e Navegação (PyQt6 + PyMuPDF)
O sistema realiza a leitura dos documentos PDF com recursos de Zoom via `Ctrl + Scroll` e navegação de páginas através de atalhos de teclado e de campos editáveis. A área de visualização possui suporte a "Modo Escuro" com inversão de pixels para conforto visual. Além disso, a aba de biblioteca conta com um layout em grade responsivo, que adapta a quantidade de itens por linha conforme o tamanho da janela da aplicação.

<img width="872" height="467" alt="1" src="https://github.com/user-attachments/assets/7789fe19-8383-471f-abe2-6e9128561160" />

*Demonstração do Leitor de PDF processando o livro TDD de Kent Beck, com inversão dinâmica de pixels ativada.*

### 2.2 Persistência de Dados (ChromaDB + JSON)
A resiliência de dados é garantida pelo uso do `chromadb.PersistentClient` associado a um arquivo de estado local `library.json`. O progresso de leitura, metadados dos livros abertos (capas geradas via hash) e vetores indexados são mantidos entre ciclos de vida da aplicação.

<img width="872" height="467" alt="2 - " src="https://github.com/user-attachments/assets/98861636-6f06-4a9f-ae6f-957b2fbeb11f" />

*Evidência da persistência de metadados: Geração de miniatura da capa e estado de leitura (porcentagem lida) salvos localmente.*

### 2.3 Recuperação Aumentada por Geração (RAG)
A aplicação implementa um pipeline RAG com 3 etapas de filtragem:
1. **Fragmentação Semântica (LangChain):** Evita o corte cego de frases pela metade, particionando o texto de forma coerente através de delimitadores léxicos.
2. **Busca Vetorial Expandida:** Resgate de um número expandido de blocos prováveis (top 15) direto do banco vetorial.
3. **Re-ranqueamento (Cross-Encoder):** Re-ordenação dos blocos pelo seu real nível de resposta à pergunta da vez, separando apenas o top 3 para anexar ao contexto. Junto à memória de histórico (`Chat History`), reduzindo as alucinações de dados.

<img width="872" height="467" alt="3" src="https://github.com/user-attachments/assets/cc1b5a75-b700-4326-a878-ec8b02473436" />

*Pipeline RAG em ação: LLM respondendo com base no contexto injetado e do histórico da conversa.*

### 2.4 Evolução do Modelo de Embeddings (Otimização Multilíngue)
Para mitigar a limitação da IA alegar a *"falta de informações"* (algo comum quando o Retriever falha em cruzar intenções semânticas de idiomas não-nativos), o sistema passou a sua busca vetorial trocando o `all-MiniLM-L6-v2` (focado em inglês) pelo modelo `paraphrase-multilingual-MiniLM-L12-v2` (treinado nativamente em mais de 50 idiomas, com forte suporte ao português). 

O script de teste contido neste repositório (`test_embeddings.py`) atua como prova de conceito, demonstrando que o modelo Multilíngue consegue parear sentenças em português com melhor contexto, provendo o bloco textual melhor para o *Llama 3.2* formular a resposta.

## 3. Fluxo de Arquitetura

1.  **Ingestão e Chunking Semântico:** O **PyMuPDF** extrai o texto que é particionado pelo `RecursiveCharacterTextSplitter` (LangChain).
2.  **Processamento Background:** Uma **QThread** assíncrona absorve os blocos e gera vetores multidimensionais (embeddings).
3.  **Armazenamento Vetorial:** O **ChromaDB** gerencia os embeddings em persistência de disco.
4.  **Recuperação e Re-ranqueamento:** A pergunta aciona o banco para resgatar até 15 fragmentos. Um modelo auxiliar `Cross-Encoder` atribui notas a esses fragmentos, filtrando apenas os 3 melhores.
5.  **Inferência e Memória:** O contexto purificado, juntamente com o *histórico da conversa*, é submetido via REST API ao Ollama (`/api/chat`), que devolve a resposta final em formato HTML.

## 4. Tecnologias e Ferramentas (Stack)

*   **Interface Gráfica (GUI):** PyQt6
*   **Processamento de PDF:** PyMuPDF (`fitz`)
*   **Fragmentação Semântica:** `langchain-text-splitters`
*   **Embeddings de Linguagem:** `sentence-transformers` (Modelo Multilíngue: `paraphrase-multilingual-MiniLM-L12-v2`)
*   **Banco de Dados Vetorial:** ChromaDB (Persistente Local)
*   **Filtro Re-ranqueador:** `cross-encoder` (Modelo: `ms-marco-MiniLM-L-6-v2`)
*   **Motor de Inteligência Artificial:** Ollama executando localmente o modelo `llama3.2`

## 5. Motivação e Escolhas Arquiteturais (Trade-offs)

*   **Ollama Local vs APIs de Nuvem:** A escolha do **Ollama** foi baseada na isenção de custos. Por rodar o modelo Llama, ele consome recursos do host em vez de depender de requisições de rede, proporcionando o uso offline e mais rápido.
*   **Processamento em QThread vs Síncrono:** Para evitar o processo de congelamento visual ao se mudar de página no PDF, foi adotado o processamento em **QThread**. O sistema extrai e indexa textos para o banco vetorial de forma assíncrona, mantendo a responsividade do `PyMuPDF`.
*   **ChromaDB Local vs Banco de Dados em Nuvem:** A configuração do ChromaDB com armazenamento persistente em disco traz uma gestão de maior confiança do conhecimento, permitindo testar e reter os vetores de indexação dos PDFs mesmo após o encerramento do app.

## 6. Desafios Enfrentados e Soluções

*   **Baixa Eficiência da Busca Vetorial em Português:** 
    *   *Desafio:* Os modelos tradicionais orientados a inglês perdiam nuances da língua nativa do usuário, trazendo resultados irrelevantes para as perguntas.
    *   *Solução:* Adoção de um modelo multilíngue atualizado (`paraphrase-multilingual-MiniLM-L12-v2`) em conjunto com a aplicação técnica de re-ranqueamento com Cross-Encoder (`ms-marco-MiniLM-L-6-v2`), que atua validando a correspondência final entre a base vetorial e a pergunta.
*   **Alucinação e Limite de Contexto do LLM:**
    *   *Desafio:* Fazer com que a inferência do LLM não tentasse adivinhar respostas fora do contexto do livro atual ou se perdesse em uma massa grande de informações injetadas.
    *   *Solução:* Implementação do Cross-Encoder listado acima para extrair e repassar somente o Top 3 blocos de maior relevancia do fragmento, além da passagem do histórico de Chat (`Chat History`) para memória e as conexões coerentes com o tópico em discussão.

## 7. Estrutura do Projeto

```text
projeto/
├── covers/               # Diretório dinâmico com miniaturas extraídas das capas
├── chroma_db/            # Banco de dados vetorial gerenciado pelo ChromaDB
├── src/                  # Código-fonte principal da aplicação
│   ├── core/             # Lógica de negócio e integração (RAG, Chroma, Ollama)
│   └── ui/               # Componentes da Interface de Usuário (Biblioteca, Leitor, Chat)
├── main.py               # Controlador Principal (Orquestrador da aplicação)
├── library.json          # Estado JSON rastreando metadados de leitura
└── README.md             # Este documento técnico
```

## 8. Execução

### Passo a Passo

1.  **Pré-requisitos de IA:**
    *   Ter o [Ollama](https://ollama.com/) instalado no Windows.
    *   Fazer o download prévio do modelo abrindo um terminal e rodando:
    ```powershell
    ollama run llama3.2
    ```

2. **Preparação do Ambiente Python:** 
    ```powershell
    # Criar e ativar o ambiente virtual
    py -3.12 -m venv venv_rag
    .\venv_rag\Scripts\activate

    # Instalar a Stack tecnológica requerida
    pip install .\requirements.txt
    ```

3.  **Iniciando a Plataforma:**
    ```powershell
    # Rodar o código principal via Python dentro do venv ativado
    python main.py
    ```
