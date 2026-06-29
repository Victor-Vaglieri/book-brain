import requests
from PyQt6.QtCore import QThread, pyqtSignal
from config import OLLAMA_API_URL, OLLAMA_MODEL

class ChatThread(QThread):
    # Emit(origin: str, ai_response: str)
    # The UI is responsible for formatting this data into HTML
    response_signal = pyqtSignal(str, str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, prompt: str, rag_pipeline, document_name: str, use_local_filter: bool, chat_history: list = None) -> None:
        super().__init__()
        self.prompt = prompt
        self.rag = rag_pipeline
        self.document_name = document_name
        self.use_local_filter = use_local_filter
        self.chat_history = chat_history if chat_history else []
        
    def run(self) -> None:
        try:
            query_emb = self.rag.embedder.encode([self.prompt]).tolist()
            
            where_clause = None
            if self.use_local_filter and self.document_name:
                where_clause = {"document": self.document_name}
                
            results = self.rag.collection.query(
                query_embeddings=query_emb,
                n_results=25,
                where=where_clause
            )
            
            contexto = ""
            paginas = set()
            
            if results['documents'] and len(results['documents'][0]) > 0:
                docs = results['documents'][0]
                metadatas = results['metadatas'][0]
                
                cross_inputs = [[self.prompt, doc] for doc in docs]
                scores = self.rag.cross_encoder.predict(cross_inputs)
                
                scored_docs = sorted(zip(scores, docs, metadatas), key=lambda x: x[0], reverse=True)
                
                top_k = scored_docs[:8]
                
                context_docs = []
                for score, doc, meta in top_k:
                    context_docs.append(doc)
                    if meta and "page" in meta:
                        paginas.add(int(meta["page"]))
                contexto = "\n\n".join(context_docs)
                        
            paginas_str = ", ".join([str(p) for p in sorted(list(paginas))])
                
            if contexto:
                full_prompt = (
                    "Você é um assistente especialista de leitura. Responda à pergunta baseando-se PRIMEIRO no contexto abaixo extraído do documento. "
                    "Se a resposta não estiver completamente no contexto, você pode usar seu conhecimento geral para COMPLEMENTAR, "
                    "mas SEMPRE avise o que veio do documento e o que é seu conhecimento prévio. Seja didático, claro e organize bem as informações.\n\n"
                    f"[CONTEXTO EXTRAÍDO DAS PÁGINAS {paginas_str}]:\n{contexto}\n\n[PERGUNTA]: {self.prompt}"
                )
            else:
                full_prompt = self.prompt
                
            messages = self.chat_history.copy()
            messages.append({"role": "user", "content": full_prompt})
            
            payload = {
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "options": {
                    "num_ctx": 8192,
                    "temperature": 0.6
                }
            }
            
            response = requests.post(OLLAMA_API_URL, json=payload)
            response.raise_for_status()
            resposta_ia = response.json().get("message", {}).get("content", "")
            
            origem = f"Lendo Páginas: {paginas_str}" if (self.use_local_filter and contexto) else "Busca Global / Sem Contexto"
            
            self.response_signal.emit(origem, resposta_ia)
                    
        except requests.exceptions.ConnectionError:
            self.error_signal.emit("Falha de conexão. Verifique se o serviço local do Ollama está ativo.")
        except Exception as e:
            self.error_signal.emit(str(e))
