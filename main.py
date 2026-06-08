import sys
import fitz
import requests
from PyQt6.QtWidgets import (QApplication, QMainWindow, QSplitter, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,QPushButton, QLabel, QFileDialog, QScrollArea, QCheckBox)
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from rag import RAGPipeline, IngestionThread

class ChatThread(QThread):
    # QThread dedicada para inferência do modelo LLM e consulta ao banco vetorial.
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
            n_results=3,
            where=where_clause
        )
        
        contexto = ""
        if results['documents'] and len(results['documents'][0]) > 0:
            contexto = "\n\n".join(results['documents'][0])
            
        if contexto:
            full_prompt = f"Baseado no contexto extraído, responda à pergunta. Se não houver informação, avise.\n\nContexto:\n{contexto}\n\nPergunta: {self.prompt}"
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
            
            origem = f"Contexto: {self.document_name}" if self.use_local_filter else "Contexto: Biblioteca Global"
            if contexto:
                self.response_signal.emit(f"<br><b>Llama 3.2 ({origem}):</b><br>{resposta_ia}")
            else:
                self.response_signal.emit(f"<br><b>Llama 3.2 (Sem contexto):</b><br>{resposta_ia}")
                
        except Exception as e:
            self.response_signal.emit(f"<br><b style='color:red;'>Erro na API Ollama:</b> {e}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema RAG Inteligente - Leitor de PDF")
        self.resize(1200, 800)

        self.doc = None
        self.current_page = 0
        self.document_name = ""
        self.zoom_level = 2.0
        self.dark_mode_pdf = False

        # Inicialização do pipeline RAG
        self.rag = RAGPipeline()
        self.ingestion_thread = IngestionThread(self.rag)
        self.ingestion_thread.finished_signal.connect(self.log_to_status)
        self.ingestion_thread.start()
        self.chat_thread = None

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)

        # Configuração do painel de PDF
        self.pdf_container = QWidget()
        pdf_layout = QVBoxLayout(self.pdf_container)
        
        self.scroll_area = QScrollArea()
        self.pdf_viewer = QLabel("Aguardando documento...")
        self.pdf_viewer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pdf_viewer.setStyleSheet("background-color: #2b2b2b; color: #a9a9a9; font-size: 16px;")
        
        self.scroll_area.setWidget(self.pdf_viewer)
        self.scroll_area.setWidgetResizable(True)
        pdf_layout.addWidget(self.scroll_area, stretch=1)
        
        toolbar_layout = QHBoxLayout()
        self.btn_open = QPushButton("Abrir PDF")
        self.btn_prev = QPushButton("Anterior")
        self.btn_next = QPushButton("Próxima")
        
        self.btn_zoom_out = QPushButton("Zoom -")
        self.btn_zoom_in = QPushButton("Zoom +")
        self.chk_dark_pdf = QCheckBox("Modo Escuro")
        
        self.btn_open.clicked.connect(self.open_pdf)
        self.btn_prev.clicked.connect(self.prev_page)
        self.btn_next.clicked.connect(self.next_page)
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        self.chk_dark_pdf.stateChanged.connect(self.toggle_dark_pdf)
        
        toolbar_layout.addWidget(self.btn_open)
        toolbar_layout.addWidget(self.btn_prev)
        toolbar_layout.addWidget(self.btn_next)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.btn_zoom_out)
        toolbar_layout.addWidget(self.btn_zoom_in)
        toolbar_layout.addWidget(self.chk_dark_pdf)
        
        pdf_layout.addLayout(toolbar_layout)

        # Configuração do painel de Chat
        self.chat_container = QWidget()
        chat_layout = QVBoxLayout(self.chat_container)
        
        top_chat_layout = QHBoxLayout()
        self.chk_local_filter = QCheckBox("Restringir busca ao documento atual")
        self.chk_local_filter.setChecked(True)
        top_chat_layout.addWidget(self.chk_local_filter)
        chat_layout.addLayout(top_chat_layout)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("background-color: #1e1e1e; color: white; font-size: 14px;")
        self.chat_display.append("<b>Sistema:</b> Chatbot RAG inicializado.")
        chat_layout.addWidget(self.chat_display)
        
        self.status_log = QLabel("Status: Ocioso.")
        self.status_log.setStyleSheet("color: #aaaaaa; font-size: 12px; font-style: italic;")
        chat_layout.addWidget(self.status_log)
        
        input_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Insira sua pergunta...")
        self.chat_input.setStyleSheet("padding: 8px; font-size: 14px;")
        self.chat_input.returnPressed.connect(self.send_message)
        
        self.btn_send = QPushButton("Enviar")
        self.btn_send.setStyleSheet("padding: 8px; font-weight: bold; background-color: #4CAF50; color: white;")
        self.btn_send.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.chat_input)
        input_layout.addWidget(self.btn_send)
        chat_layout.addLayout(input_layout)

        splitter.addWidget(self.pdf_container)
        splitter.addWidget(self.chat_container)
        splitter.setSizes([780, 420])

    def send_message(self):
        user_text = self.chat_input.text().strip()
        if not user_text:
            return
            
        self.chat_display.append(f"<br><b style='color:#4ea3e5;'>Usuário:</b> {user_text}")
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
        self.status_log.setText(f"Status: {msg}")

    def open_pdf(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Abrir arquivo PDF", "", "PDF Files (*.pdf)")
        if file_name:
            try:
                self.doc = fitz.open(file_name)
                self.current_page = 0
                self.document_name = file_name.split('/')[-1]
                self.render_page()
            except Exception as e:
                self.chat_display.append(f"<br><b style='color:red;'>Erro:</b> {e}")

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
        
        texto = page.get_text()
        self.ingestion_thread.add_page(texto, self.document_name, self.current_page + 1)

    def next_page(self):
        if self.doc and self.current_page < len(self.doc) - 1:
            self.current_page += 1
            self.render_page()
            
    def prev_page(self):
        if self.doc and self.current_page > 0:
            self.current_page -= 1
            self.render_page()

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
