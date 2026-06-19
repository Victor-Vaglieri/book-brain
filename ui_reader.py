import fitz
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QLineEdit, QCheckBox,
                             QMenu, QApplication)
from PyQt6.QtGui import QImage, QPixmap, QKeySequence, QShortcut, QPainter, QColor, QPen, QCursor
from PyQt6.QtCore import Qt, pyqtSignal, QRect

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

class PDFViewerLabel(QLabel):
    selection_finished = pyqtSignal(QRect)
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.selection_start = None
        self.selection_end = None
        self.is_selecting = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selection_start = event.position().toPoint()
            self.selection_end = self.selection_start
            self.is_selecting = True
            self.update()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_selecting:
            self.selection_end = event.position().toPoint()
            self.update()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.selection_end = event.position().toPoint()
            self.is_selecting = False
            self.update()
            
            if self.selection_start and self.selection_end:
                rect = QRect(self.selection_start, self.selection_end).normalized()
                if rect.width() > 5 and rect.height() > 5:
                    self.selection_finished.emit(rect)
        else:
            super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.is_selecting and self.selection_start and self.selection_end:
            painter = QPainter(self)
            painter.setPen(QPen(QColor(0, 120, 215), 2))
            painter.setBrush(QColor(0, 120, 215, 80))
            rect = QRect(self.selection_start, self.selection_end).normalized()
            painter.drawRect(rect)

    def clear_selection(self):
        self.selection_start = None
        self.selection_end = None
        self.is_selecting = False
        self.update()

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
        
        self.pdf_viewer = PDFViewerLabel("Aguardando carregamento...")
        self.pdf_viewer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pdf_viewer.setStyleSheet("background-color: #2b2b2b; color: #a9a9a9; font-size: 16px;")
        self.pdf_viewer.selection_finished.connect(self.handle_selection)
        
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
        shortcut_next.activated.connect(self.handle_down)
        
        shortcut_prev = QShortcut(QKeySequence(Qt.Key.Key_Up), self)
        shortcut_prev.activated.connect(self.handle_up)

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

    def handle_down(self):
        v_bar = self.scroll_area.verticalScrollBar()
        if v_bar.value() < v_bar.maximum():
            v_bar.setValue(v_bar.value() + v_bar.singleStep() * 3)
        else:
            self.next_page()
            
    def handle_up(self):
        v_bar = self.scroll_area.verticalScrollBar()
        if v_bar.value() > v_bar.minimum():
            v_bar.setValue(v_bar.value() - v_bar.singleStep() * 3)
        else:
            if self.current_page > 0:
                self.prev_page()

    def handle_selection(self, rect):
        if not self.doc:
            return
            
        pixmap = self.pdf_viewer.pixmap()
        if not pixmap:
            return
            
        offset_x = (self.pdf_viewer.width() - pixmap.width()) // 2
        offset_y = (self.pdf_viewer.height() - pixmap.height()) // 2
        offset_x = max(0, offset_x)
        offset_y = max(0, offset_y)
        
        px0 = rect.left() - offset_x
        py0 = rect.top() - offset_y
        px1 = rect.right() - offset_x
        py1 = rect.bottom() - offset_y
        
        pdf_x0 = px0 / self.zoom_level
        pdf_y0 = py0 / self.zoom_level
        pdf_x1 = px1 / self.zoom_level
        pdf_y1 = py1 / self.zoom_level
        
        pdf_rect = fitz.Rect(pdf_x0, pdf_y0, pdf_x1, pdf_y1)
        
        page = self.doc.load_page(self.current_page)
        raw_text = page.get_text("text", clip=pdf_rect).strip()
        
        import re
        text = re.sub(r'-\n\s*', '', raw_text)
        text = re.sub(r'\s*\n\s*', ' ', text).strip()
        
        annots_to_delete = []
        for annot in page.annots():
            if annot.type[0] == fitz.PDF_ANNOT_HIGHLIGHT:
                if annot.rect.intersects(pdf_rect):
                    annots_to_delete.append(annot)
        
        if text or annots_to_delete:
            menu = QMenu(self)
            action_copy = None
            action_highlight = None
            action_remove = None
            
            if text:
                action_copy = menu.addAction("Copiar texto")
                action_highlight = menu.addAction("Destacar (Marca-texto)")
            
            if annots_to_delete:
                action_remove = menu.addAction("Remover marcação")
            
            action = menu.exec(QCursor.pos())
            
            if action:
                if action == action_copy:
                    QApplication.clipboard().setText(text)
                elif action == action_highlight:
                    annot = page.add_highlight_annot(pdf_rect)
                    annot.update()
                    try:
                        self.doc.saveIncr()
                    except Exception:
                        pass
                    self.render_page()
                elif action == action_remove:
                    for annot in annots_to_delete:
                        page.delete_annot(annot)
                    try:
                        self.doc.saveIncr()
                    except Exception:
                        pass
                    self.render_page()
                
        self.pdf_viewer.clear_selection()

    def next_page(self):
        if self.doc and self.current_page < len(self.doc) - 1:
            self.current_page += 1
            self.render_page()
            from PyQt6.QtCore import QTimer
            v_bar = self.scroll_area.verticalScrollBar()
            QTimer.singleShot(50, lambda: v_bar.setValue(0))
            
    def prev_page(self):
        if self.doc and self.current_page > 0:
            self.current_page -= 1
            self.render_page()
            from PyQt6.QtCore import QTimer
            v_bar = self.scroll_area.verticalScrollBar()
            QTimer.singleShot(50, lambda: v_bar.setValue(v_bar.maximum()))

    def jump_to_page(self):
        if not self.doc:
            return
        try:
            target = int(self.page_input.text()) - 1
            if 0 <= target < len(self.doc):
                self.current_page = target
                self.render_page()
                from PyQt6.QtCore import QTimer
                v_bar = self.scroll_area.verticalScrollBar()
                QTimer.singleShot(50, lambda: v_bar.setValue(0))
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
