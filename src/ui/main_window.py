import fitz
from PyQt6.QtWidgets import QMainWindow, QSplitter, QStackedWidget
from PyQt6.QtCore import Qt, QTimer

from src.core.rag_pipeline import RAGPipeline, IngestionThread
from src.core.chat_thread import ChatThread
from src.core.library_manager import LibraryManager
from src.ui.library import LibraryWidget
from src.ui.reader import ReaderWidget
from src.ui.chat import ChatWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema RAG Inteligente - Leitor de PDF")
        self.resize(1200, 800)
        
        self.chat_history = []
        
        self.library_manager = LibraryManager()
        
        self.rag = None
        self.ingestion_thread = None
        QTimer.singleShot(500, self.init_ai_models)
        
        self.chat_thread = None

        # Configuração UI Principal
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)

        self.stacked_left = QStackedWidget()
        self.library_widget = LibraryWidget()
        self.reader_widget = ReaderWidget()
        
        self.stacked_left.addWidget(self.library_widget)
        self.stacked_left.addWidget(self.reader_widget)
        self.stacked_left.setCurrentIndex(0)

        self.chat_widget = ChatWidget()
        
        splitter.addWidget(self.stacked_left)
        splitter.addWidget(self.chat_widget)
        splitter.setSizes([780, 420])
        
        # Conexões
        self.library_widget.open_document_signal.connect(self.open_pdf_from_library)
        self.library_widget.add_document_signal.connect(self.add_book_to_library)
        self.library_widget.index_document_signal.connect(self.index_full_pdf)
        self.library_widget.remove_document_signal.connect(self.remove_book_from_library)
        
        self.reader_widget.return_to_library_signal.connect(self.close_pdf_and_return)
        self.reader_widget.page_changed_signal.connect(self.on_page_changed)
        
        self.chat_widget.send_message_signal.connect(self.send_message)


        self.library_widget.refresh_grid(self.library_manager.library_data)

    def init_ai_models(self):
        self.chat_widget.set_status("Carregando cérebro da Inteligência Artificial... Aguarde.")
        self.rag = RAGPipeline()
        self.ingestion_thread = IngestionThread(self.rag)
        self.ingestion_thread.finished_signal.connect(self.chat_widget.set_status)
        self.ingestion_thread.start()
        self.chat_widget.set_status("Inteligência Artificial Pronta!")

    def add_book_to_library(self, file_path: str):
        book = self.library_manager.add_book(file_path)
        if book:
            self.library_widget.refresh_grid(self.library_manager.library_data)
            self.open_pdf_from_library(file_path)
        else:
            self.chat_widget.set_status("Falha na importação do documento.")

    def index_full_pdf(self, file_path: str):
        if not self.ingestion_thread:
            self.chat_widget.set_status("Aguarde a inicialização da IA antes de indexar.")
            return
            
        name = file_path.split('/')[-1]
        self.chat_widget.set_status(f"Iniciando indexação completa de '{name}'...")
        
        try:
            doc = fitz.open(file_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                if text.strip():
                    self.ingestion_thread.add_page(text, name, page_num + 1)
            doc.close()
            self.chat_widget.set_status(f"'{name}' enviado para indexação em background.")
        except Exception as e:
            self.chat_widget.set_status(f"Erro ao indexar '{name}': {e}")

    def remove_book_from_library(self, file_path: str):
        book = self.library_manager.remove_book(file_path)
        if book:
            self.library_widget.refresh_grid(self.library_manager.library_data)
            name = file_path.split('/')[-1]
            if self.rag and self.rag.collection:
                try:
                    self.rag.collection.delete(where={"document": name})
                    self.chat_widget.set_status(f"O documento '{name}' foi totalmente apagado da IA e da Biblioteca.")
                except Exception as e:
                    self.chat_widget.set_status(f"Livro removido, mas houve falha ao limpar IA: {e}")
            else:
                self.chat_widget.set_status(f"O documento '{name}' foi removido da Biblioteca.")

    def open_pdf_from_library(self, file_path: str):
        current_page = self.library_manager.get_progress(file_path)
        success, msg = self.reader_widget.load_document(file_path, current_page)
        if success:
            self.stacked_left.setCurrentIndex(1)
            self.chat_widget.set_status(f"Arquivo carregado: {msg}")
        else:
            self.chat_widget.set_status(f"Erro na abertura do arquivo: {msg}")

    def close_pdf_and_return(self):
        doc_path, current_page = self.reader_widget.close_document()
        if doc_path:
            self.library_manager.update_progress(doc_path, current_page)
            self.library_widget.refresh_grid(self.library_manager.library_data)
        self.stacked_left.setCurrentIndex(0)

    def on_page_changed(self, text: str, page_num: int, doc_name: str):
        if self.ingestion_thread:
            self.ingestion_thread.add_page(text, doc_name, page_num)
        
        self.library_manager.update_progress(self.reader_widget.document_path, page_num - 1)

    def send_message(self, user_text: str, use_local_filter: bool):
        if not self.rag:
            self.chat_widget.append_error_msg("A Inteligência Artificial ainda está carregando. Tente novamente em alguns instantes.")
            return
            
        self.chat_thread = ChatThread(
            user_text, self.rag, self.reader_widget.document_name, 
            use_local_filter, self.chat_history.copy()
        )
        self.chat_history.append({"role": "user", "content": user_text})
        
        self.chat_thread.response_signal.connect(self.receive_message)
        self.chat_thread.error_signal.connect(self.chat_widget.append_error_msg)
        self.chat_thread.start()

    def receive_message(self, origin: str, raw_ai_text: str):
        self.chat_history.append({"role": "assistant", "content": raw_ai_text})
        self.chat_widget.append_ai_msg(origin, raw_ai_text)

    def closeEvent(self, event):
        if self.ingestion_thread:
            self.ingestion_thread.is_running = False
            self.ingestion_thread.wait()
        super().closeEvent(event)
