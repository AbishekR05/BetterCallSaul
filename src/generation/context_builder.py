# src/generation/context_builder.py
"""
Context Construction logic for Phase 2.6 (§3.2).
Formats selected ScoredChunks into a structured, labeled evidence block with local IDs [E1], [E2].
"""

from typing import List, Dict, Tuple, Optional
from eval.schemas import ScoredChunk


class ContextBuilder:
    """
    Formats selected evidence chunks into a structured text block for the LLM prompt.
    """

    def build_context(
        self,
        chunks: List[ScoredChunk],
        expected_jurisdiction: Optional[str] = None
    ) -> Tuple[str, Dict[str, ScoredChunk]]:
        """
        Orders and labels selected chunks into an evidence block.
        Returns: (formatted_evidence_block_text, local_id_map)
        """
        if not chunks:
            return "No relevant legal evidence retrieved.", {}

        # Sort chunks:
        # 1. Matching expected jurisdiction first
        # 2. Legislation before judgment
        # 3. High confidence before low confidence
        def sort_key(chunk: ScoredChunk):
            prov = chunk.provenance if isinstance(chunk.provenance, dict) else {}
            jur = prov.get("jurisdiction") or prov.get("level") or "central"
            doc_type = prov.get("source_type") or prov.get("document_type") or "legislation"
            conf = getattr(chunk, 'confidence_tier', 'high')

            jur_score = 0 if (expected_jurisdiction and expected_jurisdiction in str(jur).lower()) else 1
            type_score = 0 if "legis" in str(doc_type).lower() else 1
            conf_score = 0 if conf == "high" else 1

            return (jur_score, type_score, conf_score, -chunk.similarity_score)

        sorted_chunks = sorted(chunks, key=sort_key)

        local_id_map: Dict[str, ScoredChunk] = {}
        context_blocks = []

        for idx, chunk in enumerate(sorted_chunks, start=1):
            local_id = f"E{idx}"
            local_id_map[local_id] = chunk

            prov = chunk.provenance if isinstance(chunk.provenance, dict) else {}
            title = prov.get("title") or prov.get("act") or prov.get("case_name") or chunk.document_id
            doc_type = prov.get("source_type") or prov.get("document_type") or "legislation"
            jurisdiction = prov.get("jurisdiction") or prov.get("level") or "central"
            section = prov.get("section") or prov.get("citation") or "N/A"
            court = prov.get("court") or ""

            header = f"[{local_id}] Title: {title} | Type: {doc_type} | Jurisdiction: {jurisdiction}"
            if section and section != "N/A":
                header += f" | Section/Citation: {section}"
            if court:
                header += f" | Court: {court}"

            block = f"{header}\nText: {chunk.text.strip()}"
            context_blocks.append(block)

        formatted_context = "\n\n".join(context_blocks)
        return formatted_context, local_id_map
