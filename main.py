import sys
import os
import json
import hashlib
import fitz
import requests
from PyQt6.QtWidgets import (QApplication, QMainWindow, QSplitter, QWidget,
                             QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
                             QPushButton, QLabel, QFileDialog, QScrollArea, 
                             QCheckBox, QStackedWidget, QGridLayout, QFrame, QProgressBar)
from PyQt6.QtGui import QImage, QPixmap, QCursor, QKeySequence, QShortcut
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize

from rag import RAGPipeline, IngestionThread

LIBRARY_FILE = "library.json"
COVERS_DIR = "covers"

class ChatThread(QThread):
    response_signal = pyqtSignal(str)
    
    def __init__(self, prompt, rag_pipeline, document_name, use_local_filter):
        super().__init__()
        self.prompt = prompt
        self.rag = rag_pipeline
        self.document_name = document_name
        self.use_local_filter = use_local_filter
        
    def run(self):
        query_emb = self.rag.embedder.encode([self.prompt]).tolist()
        
        where_clause = None
        if self.use_local_filter and self.document_name:
            where_clause = {"document": self.document_name}
            
        results = self.rag.collection.query(
            query_embeddings=query_emb,
            n_results=5,
            where=where_clause
        )
        
        contexto = ""
        paginas = set()
        
        if results['documents'] and len(results['documents'][0]) > 0:
            contexto = "\n\n".join(results['documents'][0])
            for meta in results['metadatas'][0]:
                if meta and "page" in meta:
                    paginas.add(int(meta["page"]))
                    
        paginas_str = ", ".join([str(p) for p in sorted(list(paginas))])
            
        if contexto:
            full_prompt = f"Você é um assistente especialista. Responda EXATAMENTE baseando-se no contexto abaixo. Se a resposta não estiver no contexto, diga que não encontrou.\n\n[CONTEXTO EXTRAÍDO DAS PÁGINAS {paginas_str}]:\n{contexto}\n\n[PERGUNTA]: {self.prompt}"
        else:
            full_prompt = self.prompt
            
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": "llama3.2",
            "prompt": full_prompt,
            "stream": False
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            resposta_ia = response.json().get("response", "")
            
            origem = f"Lendo Páginas: {paginas_str}" if self.use_local_filter else "Busca Global"
            resposta_ia = resposta_ia.replace("\n", "<br>")
            
            if contexto:
                self.response_signal.emit(f"<div align='left' style='color: white; margin-bottom: 10px; background-color: #2b2b2b; padding: 10px; border-radius: 8px; margin-right: 30px;'><b>🤖 Llama 3.2 ({origem}):</b><br>{resposta_ia}</div>")
            else:
                self.response_signal.emit(f"<div align='left' style='color: white; margin-bottom: 10px; background-color: #2b2b2b; padding: 10px; border-radius: 8px; margin-right: 30px;'><b>🤖 Llama 3.2 (Sem contexto):</b><br>{resposta_ia}</div>")
                
        except requests.exceptions.ConnectionError:
            self.response_signal.emit("<div align='left' style='color: #ff4d4d; margin-bottom: 10px; background-color: #2b2b2b; padding: 10px; border-radius: 8px;'><b>Ollama Offline:</b><br>Falha de conexão. Verifique se o serviço local do Ollama está ativo.</div>")
        except Exception as e:
            self.response_signal.emit(f"<div align='left' style='color: #ff4d4d; margin-bottom: 10px; background-color: #2b2b2b; padding: 10px; border-radius: 8px;'><b>Erro:</b><br>{e}</div>")


class PDFScrollArea(QScrollArea):
    zoom_signal = pyqtSignal(bool)
    
    def wheelEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_signal.emit(True)
            else:
                self.zoom_signal.emit(False)
        else:
            super().wheelEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema RAG Inteligente - Leitor de PDF")
        self.resize(1200, 800)

        self.doc = None
        self.current_page = 0
        self.document_name = ""
        self.document_path = ""
        self.zoom_level = 2.0
        self.dark_mode_pdf = False
        
        self.library_data = []
        self.load_library()

        self.rag = RAGPipeline()
        self.ingestion_thread = IngestionThread(self.rag)
        self.ingestion_thread.finished_signal.connect(self.log_to_status)
        self.ingestion_thread.start()
        self.chat_thread = None

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)

        self.stacked_left = QStackedWidget()
        self.setup_library_ui()
        self.setup_reader_ui()
        
        self.stacked_left.addWidget(self.library_widget)
        self.stacked_left.addWidget(self.reader_widget)
        self.stacked_left.setCurrentIndex(0)

        self.chat_container = QWidget()
        chat_layout = QVBoxLayout(self.chat_container)
        
        top_chat_layout = QHBoxLayout()
        self.chk_local_filter = QCheckBox("Restringir busca ao documento atual")
        self.chk_local_filter.setChecked(True)
        top_chat_layout.addWidget(self.chk_local_filter)
        chat_layout.addLayout(top_chat_layout)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("background-color: #1e1e1e; color: white; font-size: 14px; padding: 10px;")
        self.chat_display.append("<div align='left' style='color: white; margin-bottom: 10px; background-color: #2b2b2b; padding: 10px; border-radius: 8px; margin-right: 30px;'><b>Sistema:</b><br>Chatbot inicializado e pronto para interação.</div>")
        chat_layout.addWidget(self.chat_display)
        
        self.status_log = QLabel("Status: Ocioso.")
        self.status_log.setStyleSheet("color: #aaaaaa; font-size: 12px; font-style: italic;")
        chat_layout.addWidget(self.status_log)
        
        input_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Insira a consulta...")
        self.chat_input.setStyleSheet("padding: 10px; font-size: 14px; border-radius: 5px;")
        self.chat_input.returnPressed.connect(self.send_message)
        
        self.btn_send = QPushButton("Enviar")
        self.btn_send.setStyleSheet("padding: 10px 20px; font-weight: bold; background-color: #4CAF50; color: white; border-radius: 5px;")
        self.btn_send.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.chat_input)
        input_layout.addWidget(self.btn_send)
        chat_layout.addLayout(input_layout)

        splitter.addWidget(self.stacked_left)
        splitter.addWidget(self.chat_container)
        splitter.setSizes([780, 420])
        
        self.refresh_library_grid()

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

    def setup_library_ui(self):
        self.library_widget = QWidget()
        layout = QVBoxLayout(self.library_widget)
        
        top_bar = QHBoxLayout()
        title = QLabel("📚 Biblioteca")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        self.btn_add_book = QPushButton("Adicionar Documento")
        self.btn_add_book.setStyleSheet("padding: 8px 15px; background-color: #007ACC; color: white; font-weight: bold; border-radius: 5px;")
        self.btn_add_book.clicked.connect(self.open_file_dialog)
        
        top_bar.addWidget(title)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_add_book)
        
        layout.addLayout(top_bar)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        scroll.setWidget(self.grid_container)
        layout.addWidget(scroll)

    def refresh_library_grid(self):
        for i in reversed(range(self.grid_layout.count())): 
            self.grid_layout.itemAt(i).widget().setParent(None)
            
        col = 0
        row = 0
        max_cols = 3
        
        for book in self.library_data:
            book_card = QFrame()
            book_card.setStyleSheet("QFrame { background-color: #2b2b2b; border-radius: 10px; padding: 10px; }")
            book_card.setFixedSize(220, 320)
            
            card_layout = QVBoxLayout(book_card)
            
            cover_label = QLabel()
            cover_pixmap = QPixmap(book["cover"])
            cover_label.setPixmap(cover_pixmap.scaled(180, 220, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(cover_label)
            
            title_label = QLabel(book["name"])
            title_label.setStyleSheet("font-weight: bold; color: white; font-size: 14px;")
            title_label.setWordWrap(True)
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(title_label)
            
            pct = int((book["current"] / book["total"]) * 100) if book["total"] > 0 else 0
            prog_label = QLabel(f"Lido: {pct}% (Pág. {book['current'] + 1}/{book['total']})")
            prog_label.setStyleSheet("color: #aaaaaa; font-size: 12px;")
            prog_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(prog_label)
            
            btn_read = QPushButton("Abrir")
            btn_read.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 5px; padding: 5px;")
            btn_read.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_read.clicked.connect(lambda checked, p=book["path"]: self.open_pdf_from_library(p))
            card_layout.addWidget(btn_read)
            
            self.grid_layout.addWidget(book_card, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def open_file_dialog(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Selecionar Arquivo", "", "PDF Files (*.pdf)")
        if file_name:
            self.add_book_to_library(file_name)

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
            self.refresh_library_grid()
            
            self.open_pdf_from_library(file_path)
        except Exception as e:
            self.status_log.setText(f"Falha na importação do documento: {e}")

    def setup_reader_ui(self):
        self.reader_widget = QWidget()
        pdf_layout = QVBoxLayout(self.reader_widget)
        
        top_bar = QHBoxLayout()
        self.btn_back_lib = QPushButton("Voltar")
        self.btn_back_lib.setStyleSheet("padding: 5px 10px; font-weight: bold;")
        self.btn_back_lib.clicked.connect(self.close_pdf_and_return)
        
        self.lbl_reader_title = QLabel("Leitor")
        self.lbl_reader_title.setStyleSheet("font-weight: bold; color: white;")
        
        top_bar.addWidget(self.btn_back_lib)
        top_bar.addSpacing(20)
        top_bar.addWidget(self.lbl_reader_title)
        top_bar.addStretch()
        
        pdf_layout.addLayout(top_bar)
        
        self.scroll_area = PDFScrollArea()
        self.scroll_area.zoom_signal.connect(self.handle_mouse_zoom)
        
        self.pdf_viewer = QLabel("Aguardando carregamento...")
        self.pdf_viewer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pdf_viewer.setStyleSheet("background-color: #2b2b2b; color: #a9a9a9; font-size: 16px;")
        
        self.scroll_area.setWidget(self.pdf_viewer)
        self.scroll_area.setWidgetResizable(True)
        pdf_layout.addWidget(self.scroll_area, stretch=1)
        
        bottom_bar = QHBoxLayout()
        self.btn_prev = QPushButton("Anterior")
        
        self.page_input = QLineEdit()
        self.page_input.setFixedWidth(50)
        self.page_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_input.returnPressed.connect(self.jump_to_page)
        
        self.lbl_total_pages = QLabel(" / 0")
        
        self.btn_next = QPushButton("Próxima")
        self.btn_zoom_out = QPushButton("Zoom -")
        self.btn_zoom_in = QPushButton("Zoom +")
        self.chk_dark_pdf = QCheckBox("Modo Escuro")
        
        self.btn_prev.clicked.connect(self.prev_page)
        self.btn_next.clicked.connect(self.next_page)
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        self.chk_dark_pdf.stateChanged.connect(self.toggle_dark_pdf)
        
        bottom_bar.addStretch()
        bottom_bar.addWidget(self.btn_prev)
        bottom_bar.addWidget(self.page_input)
        bottom_bar.addWidget(self.lbl_total_pages)
        bottom_bar.addWidget(self.btn_next)
        bottom_bar.addSpacing(20)
        bottom_bar.addWidget(self.btn_zoom_out)
        bottom_bar.addWidget(self.btn_zoom_in)
        bottom_bar.addWidget(self.chk_dark_pdf)
        bottom_bar.addStretch()
        
        pdf_layout.addLayout(bottom_bar)
        
        shortcut_next = QShortcut(QKeySequence(Qt.Key.Key_Down), self.reader_widget)
        shortcut_next.activated.connect(self.next_page)
        
        shortcut_prev = QShortcut(QKeySequence(Qt.Key.Key_Up), self.reader_widget)
        shortcut_prev.activated.connect(self.prev_page)

    def close_pdf_and_return(self):
        if self.doc:
            for b in self.library_data:
                if b["path"] == self.document_path:
                    b["current"] = self.current_page
                    break
            self.save_library()
            self.refresh_library_grid()
            
            self.doc.close()
            self.doc = None
            
        self.stacked_left.setCurrentIndex(0)

    def open_pdf_from_library(self, file_path):
        try:
            self.doc = fitz.open(file_path)
            self.document_path = file_path
            self.document_name = file_path.split('/')[-1]
            self.lbl_reader_title.setText(f"Documento: {self.document_name}")
            
            self.current_page = 0
            for b in self.library_data:
                if b["path"] == file_path:
                    self.current_page = b.get("current", 0)
                    break
                    
            self.stacked_left.setCurrentIndex(1)
            self.render_page()
            self.status_log.setText(f"Arquivo carregado: {self.document_name}")
        except Exception as e:
            self.status_log.setText(f"Erro na abertura do arquivo: {e}")

    def render_page(self):
        if not self.doc:
            return
            
        page = self.doc.load_page(self.current_page)
        zoom_matrix = fitz.Matrix(self.zoom_level, self.zoom_level)
        pix = page.get_pixmap(matrix=zoom_matrix)
        
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
        
        if self.dark_mode_pdf:
            img.invertPixels()
            
        pixmap = QPixmap.fromImage(img)
        self.pdf_viewer.setPixmap(pixmap)
        
        self.page_input.setText(str(self.current_page + 1))
        self.lbl_total_pages.setText(f" / {len(self.doc)}")
        
        texto = page.get_text()
        self.ingestion_thread.add_page(texto, self.document_name, self.current_page + 1)
        
        for b in self.library_data:
            if b["path"] == self.document_path:
                b["current"] = self.current_page
                break
        self.save_library()

    def next_page(self):
        if self.doc and self.current_page < len(self.doc) - 1:
            self.current_page += 1
            self.render_page()
            
    def prev_page(self):
        if self.doc and self.current_page > 0:
            self.current_page -= 1
            self.render_page()

    def jump_to_page(self):
        if not self.doc:
            return
        try:
            target = int(self.page_input.text()) - 1
            if 0 <= target < len(self.doc):
                self.current_page = target
                self.render_page()
            else:
                self.page_input.setText(str(self.current_page + 1))
        except ValueError:
            self.page_input.setText(str(self.current_page + 1))

    def handle_mouse_zoom(self, zoom_in):
        if zoom_in:
            self.zoom_in()
        else:
            self.zoom_out()

    def zoom_in(self):
        self.zoom_level += 0.5
        self.render_page()
        
    def zoom_out(self):
        if self.zoom_level > 0.5:
            self.zoom_level -= 0.5
            self.render_page()
            
    def toggle_dark_pdf(self, state):
        self.dark_mode_pdf = bool(state)
        self.render_page()

    def send_message(self):
        user_text = self.chat_input.text().strip()
        if not user_text:
            return
            
        self.chat_display.append(f"<div align='right' style='color: white; margin-bottom: 10px; background-color: #007ACC; padding: 10px; border-radius: 8px; margin-left: 30px;'><b>Usuário:</b><br>{user_text}</div>")
        self.chat_input.clear()
        
        self.chat_input.setEnabled(False)
        self.btn_send.setEnabled(False)
        
        self.chat_thread = ChatThread(user_text, self.rag, self.document_name, self.chk_local_filter.isChecked())
        self.chat_thread.response_signal.connect(self.receive_message)
        self.chat_thread.start()
        
    def receive_message(self, response_html):
        self.chat_display.append(response_html)
        self.chat_input.setEnabled(True)
        self.btn_send.setEnabled(True)
        self.chat_input.setFocus()

    def log_to_status(self, msg):
        self.status_log.setText(f"Log de Execução: {msg}")

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
