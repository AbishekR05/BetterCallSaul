# src/generation/citation_mapper.py
"""
Citation and Provenance Mapping Logic for Phase 2.6 (§7.1).
Maps local reference IDs (E1, E2) back to full provenance Citation objects.
"""

from typing import List, Dict, Tuple
from eval.schemas import ScoredChunk
from src.generation.schemas import Citation


class CitationMapper:
    """
    Resolves local citation tags into full provenance Citation objects (§7.1).
    """

    def map_citations(
        self,
        citations_used: List[str],
        local_id_map: Dict[str, ScoredChunk]
    ) -> Tuple[List[Citation], int]:
        """
        Maps local IDs in citations_used to Citation models and calculates unused evidence count.
        Returns: (citations_list, unused_evidence_count)
        """
        resolved_citations: List[Citation] = []
        cited_local_ids = set()

        for raw_id in citations_used:
            clean_id = raw_id.replace("[", "").replace("]", "").strip()
            if clean_id in local_id_map:
                cited_local_ids.add(clean_id)
                chunk = local_id_map[clean_id]
                prov = chunk.provenance if isinstance(chunk.provenance, dict) else {}

                citation_obj = Citation(
                    local_id=clean_id,
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    document_type=prov.get("source_type") or prov.get("document_type") or "legislation",
                    title=prov.get("title") or prov.get("act") or prov.get("case_name") or chunk.document_id,
                    act=prov.get("act") or "",
                    section=prov.get("section") or prov.get("citation") or "",
                    court=prov.get("court") or "",
                    jurisdiction=prov.get("jurisdiction") or prov.get("level") or "central",
                    source_url=prov.get("source_url") or "",
                    relevance_score=chunk.similarity_score
                )
                resolved_citations.append(citation_obj)

        total_provided = len(local_id_map)
        unused_evidence_count = max(0, total_provided - len(cited_local_ids))

        return resolved_citations, unused_evidence_count
