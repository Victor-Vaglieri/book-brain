import sys
import os

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

os.environ["TQDM_DISABLE"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

import json
import hashlib
import fitz
from PyQt6.QtWidgets import QApplication, QMainWindow, QSplitter, QStackedWidget
from PyQt6.QtCore import Qt

from rag import RAGPipeline, IngestionThread
from ui_library import LibraryWidget
from ui_reader import ReaderWidget
from ui_chat import ChatWidget
from chat_thread import ChatThread

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LIBRARY_FILE = os.path.join(BASE_DIR, "library.json")
COVERS_DIR = os.path.join(BASE_DIR, "covers")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema RAG Inteligente - Leitor de PDF")
        self.resize(1200, 800)
        
        self.chat_history = []
        self.library_data = []
        self.load_library()

        self.rag = RAGPipeline()
        self.ingestion_thread = IngestionThread(self.rag)
        self.ingestion_thread.start()
        
        self.chat_thread = None

        # --- Configuração da Interface (UI) ---
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
        
        # --- Conexões de Sinais (Signals) ---
        self.library_widget.open_document_signal.connect(self.open_pdf_from_library)
        self.library_widget.add_document_signal.connect(self.add_book_to_library)
        
        self.reader_widget.return_to_library_signal.connect(self.close_pdf_and_return)
        self.reader_widget.page_changed_signal.connect(self.on_page_changed)
        
        self.chat_widget.send_message_signal.connect(self.send_message)
        self.ingestion_thread.finished_signal.connect(self.chat_widget.set_status)

        self.library_widget.refresh_grid(self.library_data)

    def load_library(self):
        if not os.path.exists(COVERS_DIR):
            os.makedirs(COVERS_DIR)
            
        if os.path.exists(LIBRARY_FILE):
            with open(LIBRARY_FILE, "r", encoding="utf-8") as f:
                self.library_data = json.load(f)
        else:
            self.library_data = []
            
    def save_library(self):
        with open(LIBRARY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.library_data, f, ensure_ascii=False, indent=4)

    def add_book_to_library(self, file_path):
        for b in self.library_data:
            if b["path"] == file_path:
                self.open_pdf_from_library(file_path)
                return
                
        try:
            temp_doc = fitz.open(file_path)
            total_pages = len(temp_doc)
            name = file_path.split('/')[-1]
            
            page = temp_doc.load_page(0)
            pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
            h = hashlib.md5(file_path.encode()).hexdigest()
            cover_path = os.path.join(COVERS_DIR, f"cover_{h}.png")
            pix.save(cover_path)
            temp_doc.close()
            
            book_entry = {
                "path": file_path,
                "name": name,
                "total": total_pages,
                "current": 0,
                "cover": cover_path
            }
            self.library_data.insert(0, book_entry)
            self.save_library()
            self.library_widget.refresh_grid(self.library_data)
            
            self.open_pdf_from_library(file_path)
        except Exception as e:
            self.chat_widget.set_status(f"Falha na importação do documento: {e}")

    def open_pdf_from_library(self, file_path):
        current_page = 0
        for b in self.library_data:
            if b["path"] == file_path:
                current_page = b.get("current", 0)
                break
                
        success, msg = self.reader_widget.load_document(file_path, current_page)
        if success:
            self.stacked_left.setCurrentIndex(1)
            self.chat_widget.set_status(f"Arquivo carregado: {msg}")
        else:
            self.chat_widget.set_status(f"Erro na abertura do arquivo: {msg}")

    def close_pdf_and_return(self):
        doc_path, current_page = self.reader_widget.close_document()
        if doc_path:
            for b in self.library_data:
                if b["path"] == doc_path:
                    b["current"] = current_page
                    break
            self.save_library()
            self.library_widget.refresh_grid(self.library_data)
            
        self.stacked_left.setCurrentIndex(0)

    def on_page_changed(self, text, page_num, doc_name):
        self.ingestion_thread.add_page(text, doc_name, page_num)
        
        for b in self.library_data:
            if b["path"] == self.reader_widget.document_path:
                b["current"] = page_num - 1
                break
        self.save_library()

    def send_message(self, user_text, use_local_filter):
        self.chat_thread = ChatThread(user_text, self.rag, self.reader_widget.document_name, use_local_filter, self.chat_history.copy())
        self.chat_history.append({"role": "user", "content": user_text})
        self.chat_thread.response_signal.connect(self.receive_message)
        self.chat_thread.start()

    def receive_message(self, response_html, raw_ai_text):
        if raw_ai_text:
            self.chat_history.append({"role": "assistant", "content": raw_ai_text})
        self.chat_widget.add_response(response_html)

    def closeEvent(self, event):
        self.ingestion_thread.is_running = False
        self.ingestion_thread.wait()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
