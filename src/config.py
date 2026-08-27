# src/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "Data"
RAW_DATA_DIR = DATA_DIR / "Raw" / "Consumer"
DOCS_DIR = BASE_DIR / "Docs"

# Ensure directories exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "bettercallsaul")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# AI Models Configuration
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
EMBEDDING_DIMENSION = 384 # Dimension of all-MiniLM-L6-v2

# LLM Configuration
# Options: "ollama", "transformers"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")

TRANSFORMERS_MODEL = os.getenv("TRANSFORMERS_MODEL", "Qwen/Qwen2.5-1.5B-Instruct")
