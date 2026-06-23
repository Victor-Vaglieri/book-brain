import os
import chromadb
from sentence_transformers import SentenceTransformer, CrossEncoder
from PyQt6.QtCore import QThread, pyqtSignal
from langchain_text_splitters import RecursiveCharacterTextSplitter

import sys

class RAGPipeline:
    def __init__(self, db_path=None, model_name="paraphrase-multilingual-MiniLM-L12-v2"):
        if db_path is None:
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, "chroma_db")

        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="pdf_knowledge")
        self.embedder = SentenceTransformer(model_name)
        self.cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        
    def chunk_text(self, text, chunk_size=1000, overlap=200):
        # Fragmenta o texto usando divisores baseados em pontuação
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", ".", "?", "!", " ", ""]
        )
        chunks = splitter.split_text(text)
        return [chunk for chunk in chunks if len(chunk.strip()) > 10]

class IngestionThread(QThread):
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
