import os
import sys

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

LIBRARY_FILE = os.path.join(DATA_DIR, "library.json")
COVERS_DIR = os.path.join(ASSETS_DIR, "covers")
CHROMA_DB_DIR = os.path.join(DATA_DIR, "chroma_db")
STYLE_FILE = os.path.join(ASSETS_DIR, "style.qss")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(COVERS_DIR, exist_ok=True)

OLLAMA_API_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3.2"

EMBEDDER_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
