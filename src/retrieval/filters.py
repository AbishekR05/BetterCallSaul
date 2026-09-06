# src/retrieval/filters.py
"""
Composable SQL WHERE clause builder for Phase 2.3 metadata filtering.
Ensures 100% parameterized SQL queries with zero SQL injection risk.
Uses aliases 'c' for chunks and 'd' for source_documents matching search.py.
"""

from typing import Tuple, List, Any, Optional
from src.retrieval.config import RetrievalFilters


def build_sql_where_clause(filters: Optional[RetrievalFilters]) -> Tuple[str, List[Any]]:
    """
    Constructs parameterized SQL WHERE clause conditions and parameter list.
    
    Returns:
      (where_clause_sql_str, param_list)
      Example where_clause_sql_str: " WHERE LOWER(d.jurisdiction) = LOWER(%s) AND LOWER(c.source_type) = LOWER(%s) "
    """
    if not filters:
        return "", []
        
    conditions: List[str] = []
    params: List[Any] = []
    
    # 1. Jurisdiction (d.jurisdiction)
    if filters.jurisdiction:
        conditions.append("LOWER(d.jurisdiction) = LOWER(%s)")
        params.append(filters.jurisdiction)
        
    # 2. Level (d.level)
    if filters.level:
        conditions.append("LOWER(d.level) = LOWER(%s)")
        params.append(filters.level)
        
    # 3. Source Type (c.source_type)
    if filters.source_type:
        conditions.append("LOWER(c.source_type) = LOWER(%s)")
        params.append(filters.source_type)
        
    # 4. Court (d.court - Judgments only)
    if filters.court:
        conditions.append("LOWER(d.court) = LOWER(%s)")
        params.append(filters.court)
        
    # 5. Domains (c.document_id)
    if filters.domains and len(filters.domains) > 0:
        domain_placeholders = ", ".join(["%s"] * len(filters.domains))
        conditions.append(f"""
            c.document_id IN (
                SELECT document_id FROM document_domains 
                JOIN domains ON document_domains.domain_id = domains.domain_id 
                WHERE LOWER(domains.domain_name) IN ({domain_placeholders})
            )
        """)
        for dom in filters.domains:
            params.append(dom.lower())
            
    # 6. Date filters (d.date)
    if filters.date_after:
        conditions.append("d.date >= %s")
        params.append(filters.date_after)
    if filters.date_before:
        conditions.append("d.date <= %s")
        params.append(filters.date_before)
        
    # 7. Effective Date filters (d.effective_date)
    if filters.effective_date_after:
        conditions.append("d.effective_date >= %s")
        params.append(filters.effective_date_after)
    if filters.effective_date_before:
        conditions.append("d.effective_date <= %s")
        params.append(filters.effective_date_before)
        
    if not conditions:
        return "", []
        
    where_sql = " WHERE " + " AND ".join(conditions) + " "
    return where_sql, params
