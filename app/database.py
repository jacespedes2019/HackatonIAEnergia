from typing import Optional
from app.config import supabase_client
from app.models import Lead

# All comments in English

TABLE_NAME = "Lead"  # real table name in Supabase


def get_next_pending_lead() -> Optional[Lead]:
    """Return one lead with status PENDING (or first available)."""
    resp = (
        supabase_client.table(TABLE_NAME)
        .select("*")
        .eq("last_call_status", "PENDING")
        .limit(1)
        .execute()
    )
    if not resp.data:
        return None
    return Lead(**resp.data[0])


def get_lead_by_id(lead_id: str) -> Lead:
    """Return a lead by its ID (UUID string)."""
    resp = (
        supabase_client.table(TABLE_NAME)
        .select("*")
        .eq("id", lead_id)
        .single()
        .execute()
    )
    if not resp.data:
        raise ValueError("Lead not found for this id")
    return Lead(**resp.data)


def update_lead_status(lead_id: str, status: str):
    """Update the last_call_status of a lead."""
    supabase_client.table(TABLE_NAME).update(
        {"last_call_status": status}
    ).eq("id", lead_id).execute()


def get_lead_by_phone(phone: str) -> Lead:
    """Return a lead by its phone number."""
    # phone_number is an integer column, so cast the incoming string
    try:
        phone_int = int(phone)
    except ValueError:
        raise ValueError("Phone must be numeric")

    resp = (
        supabase_client.table(TABLE_NAME)
        .select("*")
        .eq("phone_number", phone_int)
        .single()
        .execute()
    )
    if not resp.data:
        raise ValueError("Lead not found for this phone")
    return Lead(**resp.data)