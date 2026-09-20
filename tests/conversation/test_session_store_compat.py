# tests/conversation/test_session_store_compat.py
"""
Phase 2.7 Orchestrator Compatibility Suite for Phase 2.8 (§15, §20).
Executes Phase 2.7 orchestrator integration tests against both InMemorySessionStore and PersistentSessionStore.
"""

import pytest
from src.generation.llm_client import MockLLMClient
from src.conversation.orchestrator import ConversationalOrchestrator
from src.conversation.session_store import InMemorySessionStore
from src.conversation.persistent_session_store import PersistentSessionStore


class DummyRetrieverAdapter:
    def retrieve(self, query: str, top_k: int = 10, filters=None):
        return []


@pytest.mark.parametrize("store_type", ["in_memory", "persistent_sqlite"])
def test_orchestrator_compatibility_both_stores(store_type, tmp_path):
    mock_retriever = DummyRetrieverAdapter()
    mock_llm = MockLLMClient(canned_response_mode="sufficient")

    if store_type == "in_memory":
        store = InMemorySessionStore()
    else:
        db_file = str(tmp_path / f"compat_{store_type}.sqlite")
        store = PersistentSessionStore(backend="sqlite", sqlite_path=db_file)

    orchestrator = ConversationalOrchestrator(
        session_store=store,
        retriever_adapter=mock_retriever,
        llm_client=mock_llm
    )

    # 1. Single turn
    res1 = orchestrator.handle_turn(None, "What is the Shops and Establishments Act in Maharashtra?")
    session_id = res1.session_id
    assert session_id is not None
    assert res1.turn.turn_index == 1

    # 2. Multi-turn follow-up
    res2 = orchestrator.handle_turn(session_id, "What about Karnataka?")
    assert res2.session_id == session_id
    assert res2.turn.turn_index == 2
    assert res2.turn.followup_classification == "simple_followup"

    # 3. Isolation check
    res_other = orchestrator.handle_turn(None, "Unrelated session query")
    assert res_other.session_id != session_id
    assert res_other.turn.turn_index == 1
