import json
import os
import hashlib
import fitz
import logging
from config import LIBRARY_FILE, COVERS_DIR

class LibraryManager:
    def __init__(self) -> None:
        self.library_data: list[dict] = []
        self.load_library()

    def load_library(self) -> None:
        if os.path.exists(LIBRARY_FILE):
            try:
                with open(LIBRARY_FILE, "r", encoding="utf-8") as f:
                    self.library_data = json.load(f)
            except json.JSONDecodeError as e:
                logging.error(f"Erro ao ler biblioteca JSON: {e}")
                self.library_data = []
        else:
            self.library_data = []

    def save_library(self) -> None:
        try:
            with open(LIBRARY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.library_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logging.error(f"Erro ao salvar biblioteca JSON: {e}")

    def add_book(self, file_path: str) -> dict | None:
        # Se já existir, retorna o livro
        for b in self.library_data:
            if b["path"] == file_path:
                return b

        try:
            temp_doc = fitz.open(file_path)
            total_pages = len(temp_doc)
            name = os.path.basename(file_path)
            
            page = temp_doc.load_page(0)
            pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
            
            h = hashlib.md5(file_path.encode('utf-8')).hexdigest()
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
            return book_entry
        except Exception as e:
            logging.error(f"Falha ao extrair PDF {file_path}: {e}")
            return None

    def remove_book(self, file_path: str) -> dict | None:
        book_to_remove = next((b for b in self.library_data if b["path"] == file_path), None)
        
        if book_to_remove:
            self.library_data.remove(book_to_remove)
            self.save_library()
            try:
                if os.path.exists(book_to_remove["cover"]):
                    os.remove(book_to_remove["cover"])
            except Exception as e:
                logging.warning(f"Não foi possível remover a capa {book_to_remove['cover']}: {e}")
                
        return book_to_remove

    def update_progress(self, file_path: str, current_page: int) -> None:
        for b in self.library_data:
            if b["path"] == file_path:
                b["current"] = current_page
                self.save_library()
                break

    def get_progress(self, file_path: str) -> int:
        for b in self.library_data:
            if b["path"] == file_path:
                return b.get("current", 0)
        return 0
