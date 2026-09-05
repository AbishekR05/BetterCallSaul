# src/db_phase2.py
"""
Phase 2.2 Database Management Module for PostgreSQL 18 + pgvector.
Manages schema creation in bcs_tablespace (d:/Abishek/pg_tablespace),
relational table setup, pgvector 768-dimensional type, and high-performance COPY bulk loads.
"""

import os
import io
import csv
import psycopg
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "bettercallsaul")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "ABISHEK1995")

def get_connection(dbname=DB_NAME, autocommit=False):
    """Establish and return a connection to PostgreSQL."""
    conn = psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=dbname,
        user=DB_USER,
        password=DB_PASSWORD,
        autocommit=autocommit
    )
    return conn

def init_db_schema():
    """
    Initialize vector extension, bcs_tablespace, and relational schema for Phase 2.2.
    Tables created in bcs_tablespace:
      - source_documents
      - domains
      - document_domains
      - chunks
      - embeddings
    """
    conn = get_connection(autocommit=True)
    cursor = conn.cursor()

    # 1. Enable vector extension
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Ensure bcs_tablespace exists (or fallback to pg_default if error)
    try:
        tablespace_path = "d:/Abishek/pg_tablespace"
        if not os.path.exists(tablespace_path):
            os.makedirs(tablespace_path, exist_ok=True)
        cursor.execute(f"CREATE TABLESPACE bcs_tablespace LOCATION '{tablespace_path}';")
    except psycopg.errors.DuplicateObject:
        pass  # Tablespace already exists
    except Exception as e:
        print(f"Tablespace notice: {e}")

    # 3. Create relational schema inside transaction
    with get_connection(autocommit=False) as conn:
        with conn.cursor() as cur:
            # Source documents table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS source_documents (
                    document_id VARCHAR(255) PRIMARY KEY,
                    source_type VARCHAR(50) NOT NULL,
                    title TEXT,
                    act TEXT,
                    case_name TEXT,
                    citation TEXT,
                    court TEXT,
                    jurisdiction VARCHAR(100),
                    level VARCHAR(50),
                    state VARCHAR(100),
                    date VARCHAR(50),
                    effective_date VARCHAR(50),
                    is_historical BOOLEAN DEFAULT FALSE,
                    source_url TEXT,
                    dataset_version VARCHAR(50),
                    original_source_id VARCHAR(255)
                ) TABLESPACE bcs_tablespace;
            """)

            # Domains table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS domains (
                    domain_id SERIAL PRIMARY KEY,
                    domain_name VARCHAR(100) UNIQUE NOT NULL
                ) TABLESPACE bcs_tablespace;
            """)

            # Document-Domains junction table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS document_domains (
                    document_id VARCHAR(255) REFERENCES source_documents(document_id) ON DELETE CASCADE,
                    domain_id INT REFERENCES domains(domain_id) ON DELETE CASCADE,
                    PRIMARY KEY (document_id, domain_id)
                ) TABLESPACE bcs_tablespace;
            """)

            # Chunks table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id VARCHAR(255) PRIMARY KEY,
                    document_id VARCHAR(255) REFERENCES source_documents(document_id) ON DELETE CASCADE,
                    parent_id VARCHAR(255),
                    chunk_index INT NOT NULL,
                    source_type VARCHAR(50) NOT NULL,
                    part TEXT,
                    chapter TEXT,
                    section TEXT,
                    subsection TEXT,
                    clause TEXT,
                    paragraph_number VARCHAR(50),
                    text TEXT NOT NULL,
                    char_length INT NOT NULL,
                    cross_references TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                ) TABLESPACE bcs_tablespace;
            """)

            # Embeddings table (vector 768)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    chunk_id VARCHAR(255) PRIMARY KEY REFERENCES chunks(chunk_id) ON DELETE CASCADE,
                    model_name VARCHAR(100) NOT NULL,
                    model_version VARCHAR(50),
                    embedding vector(768) NOT NULL,
                    embedded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                ) TABLESPACE bcs_tablespace;
            """)
        conn.commit()
    print("Database schema successfully initialized in bcs_tablespace!")

def bulk_copy_domains(conn, domain_names):
    """Ensure domains exist in domains table and return mapping {domain_name: domain_id}."""
    with conn.cursor() as cur:
        for name in domain_names:
            cur.execute(
                "INSERT INTO domains (domain_name) VALUES (%s) ON CONFLICT (domain_name) DO NOTHING;",
                (name,)
            )
        cur.execute("SELECT domain_name, domain_id FROM domains;")
        mapping = {row[0]: row[1] for row in cur.fetchall()}
    return mapping

def bulk_copy_source_documents(conn, docs):
    """
    Bulk load source_documents using PostgreSQL COPY.
    docs is a list of tuples/dicts.
    """
    if not docs:
        return
    
    # Prepare CSV stream in memory
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter='\t', quoting=csv.QUOTE_MINIMAL, escapechar='\\')
    
    for d in docs:
        writer.writerow([
            d.get('document_id'),
            d.get('source_type', 'unknown'),
            d.get('title', ''),
            d.get('act', ''),
            d.get('case_name', ''),
            d.get('citation', ''),
            d.get('court', ''),
            d.get('jurisdiction', ''),
            d.get('level', ''),
            d.get('state', ''),
            d.get('date', ''),
            d.get('effective_date', ''),
            d.get('is_historical', False),
            d.get('source_url', ''),
            d.get('dataset_version', '1.0'),
            d.get('original_source_id', '')
        ])
    
    buf.seek(0)
    with conn.cursor() as cur:
        # Create temp table for idempotent MERGE/ON CONFLICT COPY
        cur.execute("""
            CREATE TEMP TABLE temp_source_docs (LIKE source_documents INCLUDING DEFAULTS) ON COMMIT DROP;
        """)
        with cur.copy("COPY temp_source_docs (document_id, source_type, title, act, case_name, citation, court, jurisdiction, level, state, date, effective_date, is_historical, source_url, dataset_version, original_source_id) FROM STDIN WITH (FORMAT csv, DELIMITER '\t', ESCAPE '\\')") as copy:
            copy.write(buf.getvalue())
            
        cur.execute("""
            INSERT INTO source_documents 
            SELECT * FROM temp_source_docs 
            ON CONFLICT (document_id) DO NOTHING;
        """)

def bulk_copy_document_domains(conn, doc_domains):
    """Bulk load document_domains junction rows."""
    if not doc_domains:
        return
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter='\t')
    for doc_id, domain_id in doc_domains:
        writer.writerow([doc_id, domain_id])
    buf.seek(0)
    
    with conn.cursor() as cur:
        cur.execute("CREATE TEMP TABLE temp_doc_domains (document_id VARCHAR(255), domain_id INT) ON COMMIT DROP;")
        with cur.copy("COPY temp_doc_domains (document_id, domain_id) FROM STDIN WITH (FORMAT csv, DELIMITER '\t')") as copy:
            copy.write(buf.getvalue())
        cur.execute("""
            INSERT INTO document_domains (document_id, domain_id)
            SELECT document_id, domain_id FROM temp_doc_domains
            ON CONFLICT (document_id, domain_id) DO NOTHING;
        """)

def bulk_copy_chunks(conn, chunks_list):
    """Bulk load chunks using PostgreSQL COPY."""
    if not chunks_list:
        return
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter='\t', quoting=csv.QUOTE_MINIMAL, escapechar='\\')
    
    for c in chunks_list:
        writer.writerow([
            c.get('chunk_id'),
            c.get('document_id'),
            c.get('parent_id', ''),
            c.get('chunk_index', 0),
            c.get('source_type', 'unknown'),
            c.get('part', ''),
            c.get('chapter', ''),
            c.get('section', ''),
            c.get('subsection', ''),
            c.get('clause', ''),
            c.get('paragraph_number', ''),
            c.get('text', ''),
            c.get('char_length', len(c.get('text', ''))),
            c.get('cross_references', '')
        ])
    buf.seek(0)
    
    with conn.cursor() as cur:
        cur.execute("CREATE TEMP TABLE temp_chunks (LIKE chunks INCLUDING DEFAULTS) ON COMMIT DROP;")
        with cur.copy("COPY temp_chunks (chunk_id, document_id, parent_id, chunk_index, source_type, part, chapter, section, subsection, clause, paragraph_number, text, char_length, cross_references) FROM STDIN WITH (FORMAT csv, DELIMITER '\t', ESCAPE '\\')") as copy:
            copy.write(buf.getvalue())
        cur.execute("""
            INSERT INTO chunks (chunk_id, document_id, parent_id, chunk_index, source_type, part, chapter, section, subsection, clause, paragraph_number, text, char_length, cross_references)
            SELECT chunk_id, document_id, parent_id, chunk_index, source_type, part, chapter, section, subsection, clause, paragraph_number, text, char_length, cross_references FROM temp_chunks
            ON CONFLICT (chunk_id) DO NOTHING;
        """)

def bulk_copy_embeddings(conn, embeddings_list):
    """
    Bulk load embeddings using PostgreSQL COPY.
    embeddings_list contains tuples: (chunk_id, model_name, model_version, vector_list_str)
    vector_list_str format: '[0.123, -0.456, ...]'
    """
    if not embeddings_list:
        return
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter='\t', quoting=csv.QUOTE_MINIMAL, escapechar='\\')
    
    for chunk_id, model_name, model_version, vec_str in embeddings_list:
        writer.writerow([chunk_id, model_name, model_version, vec_str])
    buf.seek(0)
    
    with conn.cursor() as cur:
        cur.execute("CREATE TEMP TABLE temp_embeddings (LIKE embeddings INCLUDING DEFAULTS) ON COMMIT DROP;")
        with cur.copy("COPY temp_embeddings (chunk_id, model_name, model_version, embedding) FROM STDIN WITH (FORMAT csv, DELIMITER '\t', ESCAPE '\\')") as copy:
            copy.write(buf.getvalue())
        cur.execute("""
            INSERT INTO embeddings (chunk_id, model_name, model_version, embedding)
            SELECT chunk_id, model_name, model_version, embedding FROM temp_embeddings
            ON CONFLICT (chunk_id) DO NOTHING;
        """)

def create_hnsw_index(conn, m=16, ef_construction=64):
    """Build HNSW cosine vector index on embeddings(embedding)."""
    with conn.cursor() as cur:
        print(f"Building HNSW cosine vector index (m={m}, ef_construction={ef_construction})...")
        cur.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw 
            ON embeddings USING hnsw (embedding vector_cosine_ops)
            WITH (m = {m}, ef_construction = {ef_construction})
            TABLESPACE bcs_tablespace;
        """)
    conn.commit()
    print("HNSW vector index built successfully!")

def create_metadata_indexes(conn):
    """Build B-Tree indexes on relational metadata columns for fast hybrid search filtering."""
    with conn.cursor() as cur:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id) TABLESPACE bcs_tablespace;")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_source_type ON chunks(source_type) TABLESPACE bcs_tablespace;")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_source_docs_jurisdiction ON source_documents(jurisdiction) TABLESPACE bcs_tablespace;")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_doc_domains_domain ON document_domains(domain_id) TABLESPACE bcs_tablespace;")
    conn.commit()
    print("Metadata B-Tree indexes built successfully!")
