# src/db.py
import psycopg
from psycopg import sql
import json
from src.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, EMBEDDING_DIMENSION

def create_db_if_not_exists():
    """Connect to default 'postgres' database and create target database if it doesn't exist."""
    try:
        conn = psycopg.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname="postgres",
            autocommit=True
        )
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
            if not cur.fetchone():
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
                print(f"Successfully created database: {DB_NAME}")
            else:
                print(f"Database {DB_NAME} already exists.")
        conn.close()
    except Exception as e:
        print(f"Error checking/creating database: {e}")
        print("Please ensure PostgreSQL is running and credentials in src/config.py or .env are correct.")

def get_db_connection(register=True):
    """Establish connection to the target database and optionally register pgvector."""
    conn = psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME
    )
    if register:
        # Register vector type for psycopg
        from pgvector.psycopg import register_vector
        register_vector(conn)
    return conn

def init_db():
    """Initialize extension, tables and vector search indexes."""
    create_db_if_not_exists()
    
    try:
        # 1. Connect without registering vector to enable the extension
        conn = get_db_connection(register=False)
        conn.autocommit = True
        with conn.cursor() as cur:
            # Enable pgvector extension
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            print("pgvector extension enabled in database.")
        conn.close()
        
        # 2. Reconnect and register vector to create tables and indexes
        conn = get_db_connection(register=True)
        conn.autocommit = True
        with conn.cursor() as cur:
            # Create documents table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    filename TEXT UNIQUE NOT NULL,
                    title TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            print("Table 'documents' checked/created.")
            
            # Create chunks table with vector column
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS chunks (
                    id SERIAL PRIMARY KEY,
                    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                    page_number INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding VECTOR({EMBEDDING_DIMENSION}),
                    metadata JSONB DEFAULT '{{}}'::jsonb
                );
            """)
            print("Table 'chunks' checked/created.")
            
            # Create HNSW vector index for cosine distance
            cur.execute("""
                CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw_idx 
                ON chunks USING hnsw (embedding vector_cosine_ops);
            """)
            print("Vector search index checked/created.")
            
        conn.close()
        print("Database initialization successful.")
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise e
