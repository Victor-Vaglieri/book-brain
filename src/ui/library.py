import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QGridLayout, QFrame, QFileDialog)
from PyQt6.QtGui import QPixmap, QCursor
from PyQt6.QtCore import Qt, pyqtSignal

class BookCardWidget(QFrame):
    def __init__(self, book: dict, parent=None):
        super().__init__(parent)
        self.book = book
        self.setObjectName("bookCard")
        self.setFixedSize(220, 320)
        
        self.btn_read = QPushButton("Abrir")
        self.btn_index = QPushButton("Indexar Livro")
        self.btn_remove = QPushButton("X")
        
        self.setup_ui()
        
    def setup_ui(self):
        card_layout = QVBoxLayout(self)
        
        cover_label = QLabel()
        cover_pixmap = QPixmap(self.book["cover"])
        cover_label.setPixmap(cover_pixmap.scaled(180, 220, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(cover_label)
        
        title_label = QLabel(self.book["name"])
        title_label.setObjectName("bookTitle")
        title_label.setWordWrap(True)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title_label)
        
        pct = int((self.book["current"] / self.book["total"]) * 100) if self.book["total"] > 0 else 0
        prog_label = QLabel(f"Lido: {pct}% (Pág. {self.book['current'] + 1}/{self.book['total']})")
        prog_label.setObjectName("bookProgress")
        prog_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(prog_label)
        
        buttons_layout = QHBoxLayout()
        
        self.btn_read.setObjectName("btnRead")
        self.btn_read.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        buttons_layout.addWidget(self.btn_read)
        
        self.btn_index.setObjectName("btnIndex")
        self.btn_index.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        buttons_layout.addWidget(self.btn_index)
        
        self.btn_remove.setObjectName("btnRemove")
        self.btn_remove.setToolTip("Remover livro e limpar dados")
        self.btn_remove.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        buttons_layout.addWidget(self.btn_remove)
        
        card_layout.addLayout(buttons_layout)


class LibraryWidget(QWidget):
    open_document_signal = pyqtSignal(str)
    add_document_signal = pyqtSignal(str)
    index_document_signal = pyqtSignal(str)
    remove_document_signal = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cards = []
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        top_bar = QHBoxLayout()
        title = QLabel("📚 Biblioteca")
        title.setObjectName("titleLabel")
        
        self.btn_add_book = QPushButton("Adicionar Documento")
        self.btn_add_book.setObjectName("btnAddBook")
        self.btn_add_book.clicked.connect(self.open_file_dialog)
        
        top_bar.addWidget(title)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_add_book)
        layout.addLayout(top_bar)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        self.scroll.setWidget(self.grid_container)
        layout.addWidget(self.scroll)
        
    def refresh_grid(self, library_data: list[dict]):
        for i in reversed(range(self.grid_layout.count())): 
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                
        self.cards = []
        for book in library_data:
            card = BookCardWidget(book)
            card.btn_read.clicked.connect(lambda checked, p=book["path"]: self.open_document_signal.emit(p))
            card.btn_index.clicked.connect(lambda checked, p=book["path"]: self.index_document_signal.emit(p))
            card.btn_remove.clicked.connect(lambda checked, p=book["path"]: self.remove_document_signal.emit(p))
            self.cards.append(card)
            
        self.rearrange_grid()

    def rearrange_grid(self):
        if not hasattr(self, 'cards') or not self.cards:
            return
            
        available_width = self.scroll.viewport().width() 
        max_cols = max(1, available_width // 240)
        
        for i, card in enumerate(self.cards):
            row = i // max_cols
            col = i % max_cols
            self.grid_layout.addWidget(card, row, col)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.rearrange_grid()

    def open_file_dialog(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Selecionar Arquivo", "", "PDF Files (*.pdf)")
        if file_name:
            self.add_document_signal.emit(file_name)
