# src/planning/constraint_extractor.py
"""
Deterministic Constraint Extractor for Phase 3.4.
Scans raw/rewritten query strings for explicit court, jurisdiction, and source_type mentions.
Configured via configs/p34_metadata_constraints.yaml (§4, §5, §6).
"""

import re
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from src.planning.schemas import HardConstraints


class ConstraintExtractor:
    """
    Deterministic rule-based extractor mapping query text spans -> canonical HardConstraints.
    Never invents constraints without explicit text evidence spans.
    """
    def __init__(self, config_path: str = "configs/p34_metadata_constraints.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.canonical_courts = self.config.get("canonical_courts", {})
        self.canonical_source_types = self.config.get("canonical_source_types", {})
        self.canonical_jurisdictions = self.config.get("canonical_jurisdictions", {})

    def _load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def extract(self, query: str) -> Optional[HardConstraints]:
        """
        Extracts explicit hard constraints from raw/rewritten query string.
        Returns HardConstraints object or None if no explicit constraints found.
        """
        if not query or not query.strip():
            return None

        query_lower = query.lower()
        extracted_courts: List[str] = []
        extracted_source_type: Optional[str] = None
        extracted_jurisdiction: Optional[str] = None
        evidence_spans: Dict[str, str] = {}

        # 1. Extract Court Constraints
        for canonical_court, aliases in self.canonical_courts.items():
            # Sort aliases by length descending to match longest alias first
            sorted_aliases = sorted(aliases, key=len, reverse=True)
            for alias in sorted_aliases:
                pattern = r"\b" + re.escape(alias.lower()) + r"\b"
                match = re.search(pattern, query_lower)
                if match:
                    if canonical_court not in extracted_courts:
                        extracted_courts.append(canonical_court)
                        evidence_spans["court"] = match.group(0)
                    break

        # 2. Extract Source Type Constraints
        for canonical_st, aliases in self.canonical_source_types.items():
            sorted_aliases = sorted(aliases, key=len, reverse=True)
            for alias in sorted_aliases:
                pattern = r"\b" + re.escape(alias.lower()) + r"\b"
                match = re.search(pattern, query_lower)
                if match:
                    # Ignore weak words unless phrasing is unambiguous
                    if canonical_st not in evidence_spans:
                        extracted_source_type = canonical_st
                        evidence_spans["source_type"] = match.group(0)
                    break
            if extracted_source_type:
                break

        # 3. Extract Jurisdiction Constraints
        for canonical_jur, aliases in self.canonical_jurisdictions.items():
            sorted_aliases = sorted(aliases, key=len, reverse=True)
            for alias in sorted_aliases:
                pattern = r"\b" + re.escape(alias.lower()) + r"\b"
                match = re.search(pattern, query_lower)
                if match:
                    if "jurisdiction" not in evidence_spans:
                        extracted_jurisdiction = canonical_jur
                        evidence_spans["jurisdiction"] = match.group(0)
                    break
            if extracted_jurisdiction:
                break

        if not extracted_courts and not extracted_source_type and not extracted_jurisdiction:
            return None

        return HardConstraints(
            court=extracted_courts if extracted_courts else None,
            jurisdiction=extracted_jurisdiction,
            source_type=extracted_source_type,
            evidence_spans=evidence_spans
        )
