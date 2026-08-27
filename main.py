# main.py
import argparse
import uvicorn
from src.db import init_db
from src.ingestion import ingest_all_raw_documents
from src.retrieval import hybrid_retrieval
from src.generator import generate_rag_response

def run_cli_query(query_text: str):
    """Retrieve chunks, run generation, and print output with citations in terminal."""
    print(f"\nSearching legal database for: '{query_text}'...")
    chunks = hybrid_retrieval(query_text, limit=4)
    
    if not chunks:
        print("\n[RAG System] No relevant document chunks could be found in the database. Have you run 'python main.py ingest'?")
        return
        
    print(f"Retrieved {len(chunks)} relevant legal sections. Generating grounded answer...")
    res = generate_rag_response(query_text, chunks)
    
    print("\n" + "="*60)
    print("GROUNDED LEGAL ANSWER:")
    print("="*60)
    print(res["answer"])
    print("="*60)
    
    if res["citations"]:
        print("\nSOURCES & CITATIONS:")
        for idx, cite in enumerate(res["citations"], 1):
            print(f"{idx}. {cite['citation_key']} (File: {cite['source']}, Page {cite['page_number']})")
    print("="*60 + "\n")

def main():
    parser = argparse.ArgumentParser(
        description="BetterCallSaul - Legal Awareness Agent Baseline RAG CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # init database
    subparsers.add_parser("init", help="Initialize the database tables and enable pgvector")

    # ingest documents
    subparsers.add_parser("ingest", help="Parse PDFs in Data/Raw/Consumer and ingest to pgvector database")

    # query
    query_parser = subparsers.add_parser("query", help="Query the RAG pipeline directly via CLI")
    query_parser.add_argument("text", type=str, help="The user question / query")

    # serve
    serve_parser = subparsers.add_parser("serve", help="Start the FastAPI web server")
    serve_parser.add_argument("--host", type=str, default="127.0.0.1", help="Server host IP")
    serve_parser.add_argument("--port", type=int, default=8000, help="Server port number")

    args = parser.parse_args()

    if args.command == "init":
        print("Initializing Database...")
        init_db()
    elif args.command == "ingest":
        print("Starting Document Ingestion...")
        ingest_all_raw_documents()
    elif args.command == "query":
        run_cli_query(args.text)
    elif args.command == "serve":
        print(f"Starting API server on {args.host}:{args.port}...")
        uvicorn.run("src.app:app", host=args.host, port=args.port, reload=True)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
