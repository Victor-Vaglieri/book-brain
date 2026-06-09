import os
import chromadb
from sentence_transformers import SentenceTransformer
from PyQt6.QtCore import QThread, pyqtSignal

class RAGPipeline:
    def __init__(self, db_path="./chroma_db", model_name="all-MiniLM-L6-v2"):
        # Inicializa o cliente ChromaDB e o modelo de embeddings.
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="pdf_knowledge")
        self.embedder = SentenceTransformer(model_name)
        
    def chunk_text(self, text, chunk_size=150, overlap=30):
        # Fragmenta o texto em blocos menores (max 256 tokens do MiniLM).
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if len(chunk.strip()) > 10: # Ignora blocos quase vazios
                chunks.append(chunk)
        return chunks

class IngestionThread(QThread):
    # QThread dedicada à ingestão assíncrona de documentos no banco vetorial.
    finished_signal = pyqtSignal(str)

    def __init__(self, rag_pipeline):
        super().__init__()
        self.rag = rag_pipeline
        self.queue = []
        self.is_running = True

    def add_page(self, text, document_name, page_number):
        self.queue.append((text, document_name, page_number))

    def run(self):
        while self.is_running:
            if self.queue:
                text, doc_name, page_num = self.queue.pop(0)
                
                if not text.strip():
                    continue
                    
                chunks = self.rag.chunk_text(text)
                if chunks:
                    embeddings = self.rag.embedder.encode(chunks).tolist()
                    
                    ids = [f"{doc_name}_p{page_num}_c{i}" for i in range(len(chunks))]
                    metadatas = [{"document": doc_name, "page": page_num} for _ in chunks]
                    
                    self.rag.collection.upsert(
                        documents=chunks,
                        embeddings=embeddings,
                        metadatas=metadatas,
                        ids=ids
                    )
                    
                    self.finished_signal.emit(f"Página {page_num} indexada com sucesso.")
            else:
                self.msleep(100)
