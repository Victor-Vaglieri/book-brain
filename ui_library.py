import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QGridLayout, QFrame, QFileDialog)
from PyQt6.QtGui import QPixmap, QCursor
from PyQt6.QtCore import Qt, pyqtSignal

class LibraryWidget(QWidget):
    open_document_signal = pyqtSignal(str)
    add_document_signal = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
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
        
    def refresh_grid(self, library_data):
        for i in reversed(range(self.grid_layout.count())): 
            self.grid_layout.itemAt(i).widget().setParent(None)
            
        col = 0
        row = 0
        max_cols = 3
        
        for book in library_data:
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
            btn_read.clicked.connect(lambda checked, p=book["path"]: self.open_document_signal.emit(p))
            card_layout.addWidget(btn_read)
            
            self.grid_layout.addWidget(book_card, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def open_file_dialog(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Selecionar Arquivo", "", "PDF Files (*.pdf)")
        if file_name:
            self.add_document_signal.emit(file_name)
