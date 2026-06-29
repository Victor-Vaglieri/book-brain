from PyQt6.QtCore import QThread, pyqtSignal
from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb
from sentence_transformers import SentenceTransformer, CrossEncoder

from config import CHROMA_DB_DIR, EMBEDDER_MODEL, CROSS_ENCODER_MODEL, CHUNK_SIZE, CHUNK_OVERLAP

class RAGPipeline:
    def __init__(self) -> None:
        self.client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
        self.collection = self.client.get_or_create_collection(name="pdf_knowledge")
        self.embedder = SentenceTransformer(EMBEDDER_MODEL)
        self.cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL)
        
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ".", "?", "!", " ", ""]
        )
        
    def chunk_text(self, text: str) -> list[str]:
        chunks = self.splitter.split_text(text)
        return [chunk for chunk in chunks if len(chunk.strip()) > 10]


class IngestionThread(QThread):
    finished_signal = pyqtSignal(str)

    def __init__(self, rag_pipeline: RAGPipeline) -> None:
        super().__init__()
        self.rag = rag_pipeline
        self.queue: list[tuple[str, str, int]] = []
        self.is_running = True

    def add_page(self, text: str, document_name: str, page_number: int) -> None:
        self.queue.append((text, document_name, page_number))

    def run(self) -> None:
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
