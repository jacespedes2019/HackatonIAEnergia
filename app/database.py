from typing import Optional
from app.config import supabase_client
from app.models import Lead

# All comments in English

def get_next_pending_lead() -> Optional[Lead]:
    """Return one lead with status PENDING (or first available)."""
    resp = (
        supabase_client.table("leads")
        .select("*")
        .eq("last_call_status", "PENDING")
        .limit(1)
        .execute()
    )
    if not resp.data:
        return None
    return Lead(**resp.data[0])


def get_lead_by_id(lead_id: int) -> Lead:
    """Return a lead by its ID."""
    resp = (
        supabase_client.table("leads")
        .select("*")
        .eq("id", lead_id)
        .single()
        .execute()
    )
    return Lead(**resp.data)


def update_lead_status(lead_id: int, status: str):
    """Update the last_call_status of a lead."""
    supabase_client.table("leads").update(
        {"last_call_status": status}
    ).eq("id", lead_id).execute()