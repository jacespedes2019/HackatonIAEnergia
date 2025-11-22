from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timedelta
import os
import random

load_dotenv()

class LeadService:
    """
    LeadService
    ===========

    A thin wrapper around a Supabase client to perform CRUD operations on a "Lead" table.

    This class is designed to encapsulate common operations performed on Leads in the system:
    - retrieving leads (all, a single one, or the last non-contacted),
    - creating new leads, and
    - updating lead contact status and timestamp.

    Attributes
    ----------
    supabase : supabase.Client-like
        The Supabase client created in __init__ using environment variables:
        - os.getenv("url")  -> the Supabase project URL
        - os.getenv("key")  -> the Supabase API key
        The client is used to call .table(table_name).select/insert/update/etc. and .execute().

    Notes
    -----
    - This class assumes a database table named "Lead" exists with columns at least:
      id, name, phone_number, car_model, car_name, car_price_cop, last_call_status, last_contact_at.
    - Timestamps are stored/formatted as strings in the format YYYY-MM-DD by update_lead_status.
    - The class methods return the first row from Supabase responses (result.data[0]) when present,
      otherwise return None.
    - The implementation of get_random_lead uses .limit(1) and therefore returns the first row
      returned by the DB rather than a true random row. Use an ORDER BY random() (or DB-specific
      function) if true randomness is required.

    Methods
    -------
    __init__():
        Initialize the Supabase client used by the service.
        Environment variables:
          - "url": Supabase URL
          - "key": Supabase API key
        Raises:
          - Any exception thrown by create_client or when required environment variables are missing.

    get_all_leads():
        Retrieve all leads from the "Lead" table.
        Returns:
          - list[dict] | None: A list of lead records (dictionaries) when present; empty list if none;
            depending on Supabase client behavior this may be [] or None. The calling code should
            guard against both. Each record contains keys matching the Lead table columns.

    get_random_lead():
        Return one lead from the "Lead" table (current implementation uses limit(1)).
        Behavior:
          - Calls table("Lead").select("*").limit(1).execute() and returns the first row in result.data.
          - If no leads exist, returns None.
        Warning:
          - Despite the name, this method does not guarantee randomness. It returns the first row
            returned by the database. For random selection, modify the query to use a DB-specific
            random ordering (e.g., ORDER BY RANDOM()).

    get_last_non_contacted_lead():
        Return the most recent lead whose last_contact_at is NULL.
        Behavior:
          - Filters rows where last_contact_at IS NULL and limits to 1. Returns the first matching row
            or None if none match.
        Returns:
          - dict | None: The lead record or None.

    add_lead(name: str, phone_number: int, car_model=None, car_name=None, price=None):
        Insert a new lead into the "Lead" table.
        Parameters:
          - name (str): The lead's name. Required.
          - phone_number (int): The lead's phone number. Required (stored in phone_number column).
          - car_model (str|None): Optional car model (stored in car_model column).
          - car_name (str|None): Optional car name (stored in car_name column).
          - price (numeric|None): Optional price; stored in column car_price_cop (assumed COP currency).
        Behavior:
          - Builds a dict with provided values and explicit keys:
              {"name", "phone_number", "car_model", "car_name", "car_price_cop", "last_call_status", "last_contact_at"}
            last_call_status and last_contact_at are initialized to None.
          - Calls table("Lead").insert(data).execute().
        Returns:
          - dict | None: The inserted lead record (result.data[0]) when insertion succeeds; None otherwise.
        Raises:
          - Any exceptions propagated by the Supabase client (e.g., connection/auth errors, validation errors).

    update_lead_status(lead_id: str, new_status: str, contacted_at: datetime = None):
        Update the last_call_status and last_contact_at fields for a lead identified by id.
        Parameters:
          - lead_id (str): The id of the lead to update (used in .eq("id", lead_id)).
          - new_status (str): The new status to set in last_call_status.
          - contacted_at (datetime|None): Optional datetime specifying when the contact occurred.
            If provided, its date portion is used (formatted as "YYYY-MM-DD"). If not provided,
            the current date (datetime.now()) is used instead.
        Behavior:
          - Formats the timestamp as YYYY-MM-DD (string).
          - Calls table("Lead").update({ "last_call_status": new_status, "last_contact_at": timestamp }).eq("id", lead_id).execute()
        Returns:
          - dict | None: The updated lead record (result.data[0]) if the update succeeded and returned rows;
            otherwise None.
        Raises:
          - Any exceptions thrown by the Supabase client or from invalid input types.

    Examples
    --------
    Typical usage pattern:
        service = LeadService()
        all_leads = service.get_all_leads()
        lead = service.get_random_lead()
        new_lead = service.add_lead("Alice", 3001234567, car_model="Model X", price=120000000)
        updated = service.update_lead_status(new_lead["id"], "contacted")

    Thread-safety and concurrency
    -----------------------------
    - The class holds a Supabase client instance; whether the client is thread-safe depends on
      the underlying Supabase library. If the client is not thread-safe, create separate service
      instances per thread or use external synchronization.

    Error handling recommendations
    ------------------------------
    - Caller code should handle None returns and exceptions from the Supabase client.
    - Validate inputs (e.g., phone_number, price types) before calling add_lead/update_lead_status
      if stricter type enforcement is required.

    Extensibility
    -------------
    - Consider adding pagination, filtering parameters, and ordering options to retrieval methods.
    - Consider returning richer result objects or raising custom exceptions for clearer error handling.
    """
    def __init__(self):
        self.supabase = create_client(os.getenv("url"), os.getenv("key"))

    # ---------- Retrieval ----------

    def get_all_leads(self):
        """Returns all leads in the system."""
        return self.supabase.table("Lead").select("*").execute().data

    def get_random_lead(self):
        """Returns one random lead from the table."""
        result = self.supabase.table("Lead").select("*").limit(1).execute()
        return result.data[0] if result.data else None

    def get_last_non_contacted_lead(self):
        """Returns the most recent lead whose last_contact_at is NULL."""
        result = (
            self.supabase.table("Lead")
            .select("*")
            .is_("last_contact_at", None)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    # ---------- Create ----------

    def add_lead(self, name: str, phone_number: int, car_model=None, car_name=None, price=None):
        """Creates a new lead entry."""
        data = {
            "name": name,
            "phone_number": phone_number,
            "car_model": car_model,
            "car_name": car_name,
            "car_price_cop": price,
            "last_call_status": None,
            "last_contact_at": None
        }

        result = self.supabase.table("Lead").insert(data).execute()
        return result.data[0] if result.data else None

    # ---------- Update ----------

    def update_lead_status(self, lead_id: str, new_status: str, contacted_at: datetime = None):
        """Updates a lead's status and timestamp."""
        timestamp = contacted_at.strftime("%Y-%m-%d") if contacted_at else datetime.now().strftime("%Y-%m-%d")
        update_data = {
            "last_call_status": new_status,
            "last_contact_at": timestamp
        }
        result = (
            self.supabase.table("Lead")
            .update(update_data)
            .eq("id", lead_id)
            .execute()
        )
        return result.data[0] if result.data else None


# ----------- Example Usage -----------

if __name__ == "__main__":
    service = LeadService()

    print("\n📌 Last non-contacted lead:")
    print(service.get_last_non_contacted_lead())

    print("\n📌 Adding new lead:")
    new_lead = service.add_lead("John Doe", 3209984455, 2022, "Mazda CX-30 Touring", 129900000)
    print(new_lead)

    print("\n📌 Updating lead status:")
    if new_lead:
        updated = service.update_lead_status(new_lead["id"], "Interested")
        print(updated)