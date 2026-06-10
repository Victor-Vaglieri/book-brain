import requests
from PyQt6.QtCore import QThread, pyqtSignal

class ChatThread(QThread):
    response_signal = pyqtSignal(str, str)
    
    def __init__(self, prompt, rag_pipeline, document_name, use_local_filter, chat_history=None):
        super().__init__()
        self.prompt = prompt
        self.rag = rag_pipeline
        self.document_name = document_name
        self.use_local_filter = use_local_filter
        self.chat_history = chat_history if chat_history else []
        
    def run(self):
        query_emb = self.rag.embedder.encode([self.prompt]).tolist()
        
        where_clause = None
        if self.use_local_filter and self.document_name:
            where_clause = {"document": self.document_name}
            
        results = self.rag.collection.query(
            query_embeddings=query_emb,
            n_results=15,
            where=where_clause
        )
        
        contexto = ""
        paginas = set()
        
        if results['documents'] and len(results['documents'][0]) > 0:
            docs = results['documents'][0]
            metadatas = results['metadatas'][0]
            
            # Re-ranqueamento usando Cross-Encoder
            cross_inputs = [[self.prompt, doc] for doc in docs]
            scores = self.rag.cross_encoder.predict(cross_inputs)
            
            # Combina as pontuações com os documentos e ordena
            scored_docs = sorted(zip(scores, docs, metadatas), key=lambda x: x[0], reverse=True)
            
            # Mantém os 3 melhores (top 3)
            top_3 = scored_docs[:3]
            
            context_docs = []
            for score, doc, meta in top_3:
                context_docs.append(doc)
                if meta and "page" in meta:
                    paginas.add(int(meta["page"]))
            contexto = "\n\n".join(context_docs)
                    
        paginas_str = ", ".join([str(p) for p in sorted(list(paginas))])
            
        if contexto:
            full_prompt = f"Você é um assistente especialista. Responda EXATAMENTE baseando-se no contexto abaixo. Se a resposta não estiver no contexto, diga que não encontrou.\n\n[CONTEXTO EXTRAÍDO DAS PÁGINAS {paginas_str}]:\n{contexto}\n\n[PERGUNTA]: {self.prompt}"
        else:
            full_prompt = self.prompt
            
        messages = self.chat_history.copy()
        messages.append({"role": "user", "content": full_prompt})
        
        url = "http://localhost:11434/api/chat"
        payload = {
            "model": "llama3.2",
            "messages": messages,
            "stream": False
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            resposta_ia = response.json().get("message", {}).get("content", "")
            
            origem = f"Lendo Páginas: {paginas_str}" if self.use_local_filter else "Busca Global"
            resposta_ia_html = resposta_ia.replace("\n", "<br>")
            
            if contexto:
                self.response_signal.emit(f"<div align='left' style='color: white; margin-bottom: 10px; background-color: #2b2b2b; padding: 10px; border-radius: 8px; margin-right: 30px;'><b>🤖 Llama 3.2 ({origem}):</b><br>{resposta_ia_html}</div>", resposta_ia)
            else:
                self.response_signal.emit(f"<div align='left' style='color: white; margin-bottom: 10px; background-color: #2b2b2b; padding: 10px; border-radius: 8px; margin-right: 30px;'><b>🤖 Llama 3.2 (Sem contexto):</b><br>{resposta_ia_html}</div>", resposta_ia)
                
        except requests.exceptions.ConnectionError:
            self.response_signal.emit("<div align='left' style='color: #ff4d4d; margin-bottom: 10px; background-color: #2b2b2b; padding: 10px; border-radius: 8px;'><b>Ollama Offline:</b><br>Falha de conexão. Verifique se o serviço local do Ollama está ativo.</div>", "")
        except Exception as e:
            self.response_signal.emit(f"<div align='left' style='color: #ff4d4d; margin-bottom: 10px; background-color: #2b2b2b; padding: 10px; border-radius: 8px;'><b>Erro:</b><br>{e}</div>", "")
