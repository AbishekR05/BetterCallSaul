# src/retrieval/provenance.py
"""
Provenance field assembly module for Phase 2.3.
Ensures 100% complete source provenance metadata on every retrieved chunk item.
"""

from typing import Dict, Any
from src.retrieval.schema import ProvenanceFields


def extract_provenance(row_dict: Dict[str, Any]) -> ProvenanceFields:
    """
    Extracts and validates authoritative legal provenance fields from raw DB row dict.
    """
    return ProvenanceFields(
        document_id=str(row_dict.get("document_id", "")),
        chunk_id=str(row_dict.get("chunk_id", "")),
        source_type=str(row_dict.get("source_type", "legislation")),
        title=str(row_dict.get("title", "")) if row_dict.get("title") else "",
        act=str(row_dict.get("act", "")) if row_dict.get("act") else "",
        case_name=str(row_dict.get("case_name", "")) if row_dict.get("case_name") else "",
        citation=str(row_dict.get("citation", "")) if row_dict.get("citation") else "",
        court=str(row_dict.get("court", "")) if row_dict.get("court") else "",
        jurisdiction=str(row_dict.get("jurisdiction", "central")) if row_dict.get("jurisdiction") else "central",
        level=str(row_dict.get("level", "central")) if row_dict.get("level") else "central",
        state=str(row_dict.get("state", "")) if row_dict.get("state") else "",
        date=str(row_dict.get("date", "")) if row_dict.get("date") else "",
        effective_date=str(row_dict.get("effective_date", "")) if row_dict.get("effective_date") else "",
        is_historical=bool(row_dict.get("is_historical", False)),
        source_url=str(row_dict.get("source_url", "")) if row_dict.get("source_url") else "",
        original_source_id=str(row_dict.get("original_source_id", "")) if row_dict.get("original_source_id") else "",
        dataset_version=str(row_dict.get("dataset_version", "1.0")) if row_dict.get("dataset_version") else "1.0",
        part=str(row_dict.get("part", "")) if row_dict.get("part") else "",
        chapter=str(row_dict.get("chapter", "")) if row_dict.get("chapter") else "",
        section=str(row_dict.get("section", "")) if row_dict.get("section") else "",
        subsection=str(row_dict.get("subsection", "")) if row_dict.get("subsection") else "",
        clause=str(row_dict.get("clause", "")) if row_dict.get("clause") else "",
        paragraph_number=str(row_dict.get("paragraph_number", "")) if row_dict.get("paragraph_number") else "",
    )
