# app/conversation_store.py
from typing import Dict, List

# In-memory conversation store keyed by lead_id
_conversations: Dict[str, List[Dict[str, str]]] = {}


def get_history(lead_id: str) -> List[Dict[str, str]]:
    """Return the current history for a given lead_id."""
    return _conversations.get(lead_id, [])


def append_turn(lead_id: str, user_text: str, agent_text: str) -> None:
    """Append one conversation turn for the given lead_id."""
    hist = _conversations.setdefault(lead_id, [])
    hist.append({"user": user_text, "agent": agent_text})