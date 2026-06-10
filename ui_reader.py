import fitz
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QLineEdit, QCheckBox)
from PyQt6.QtGui import QImage, QPixmap, QKeySequence, QShortcut
from PyQt6.QtCore import Qt, pyqtSignal

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

class ReaderWidget(QWidget):
    return_to_library_signal = pyqtSignal()
    page_changed_signal = pyqtSignal(str, int, str) # texto, numero_pagina, nome_documento
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.doc = None
        self.current_page = 0
        self.document_name = ""
        self.document_path = ""
        self.zoom_level = 2.0
        self.dark_mode_pdf = False
        
        self.setup_ui()
        
    def setup_ui(self):
        pdf_layout = QVBoxLayout(self)
        
        top_bar = QHBoxLayout()
        self.btn_back_lib = QPushButton("Voltar")
        self.btn_back_lib.setStyleSheet("padding: 5px 10px; font-weight: bold;")
        self.btn_back_lib.clicked.connect(self.return_to_library_signal.emit)
        
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
        
        shortcut_next = QShortcut(QKeySequence(Qt.Key.Key_Down), self)
        shortcut_next.activated.connect(self.next_page)
        
        shortcut_prev = QShortcut(QKeySequence(Qt.Key.Key_Up), self)
        shortcut_prev.activated.connect(self.prev_page)

    def load_document(self, file_path, current_page):
        try:
            self.doc = fitz.open(file_path)
            self.document_path = file_path
            self.document_name = file_path.split('/')[-1]
            self.lbl_reader_title.setText(f"Documento: {self.document_name}")
            
            self.current_page = current_page
            self.render_page()
            return True, self.document_name
        except Exception as e:
            return False, str(e)
            
    def close_document(self):
        if self.doc:
            self.doc.close()
            self.doc = None
        return self.document_path, self.current_page

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
        self.page_changed_signal.emit(texto, self.current_page + 1, self.document_name)

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
