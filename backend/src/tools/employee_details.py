import json
import os
from typing import Optional

from livekit.agents import function_tool, RunContext

from .employee_repository import get_employee_by_id
FIELD_ALIASES: dict[str, set[str]] = {
    "name": {"name", "full_name", "employee_name", "first_name", "last_name"},
    "employee_id": {"employee_id", "id", "emp_id"},
    "email": {"email", "email_address", "mail"},
    "phone": {"phone", "mobile", "phone_number", "contact", "contact_number"},
    "department": {"department", "dept", "team"},
    "role": {"role", "employee_role", "designation", "title", "position"},
    "date_of_joining": {"date_of_joining", "doj", "joining_date", "join_date", "datejoined"},
    "location": {"location", "office", "site"},
    "manager": {"manager", "report_manager", "reporting_manager", "reporting to", "reports to", "report_to", "supervisor", "lead"},
    "status": {"status", "employment_status"},
}


def _resolve_verified_identity() -> tuple[Optional[str], Optional[str], bool]:
    """
    Resolve verified identity from the current flow session and persisted agent state.
    Returns (employee_id, employee_name, verified_flag).
    """
    employee_id: Optional[str] = None
    employee_name: Optional[str] = None
    session_verified = False
    state_verified = False

    # Prefer flow session when available
    try:
        from flow_manager import flow_manager  # type: ignore
        session = flow_manager.get_current_session()
    except Exception:
        session = None

    if session and getattr(session, "is_verified", False):
        session_verified = True
        user_data = getattr(session, "user_data", {}) or {}
        employee_id = user_data.get("employee_id") or user_data.get("manual_employee_id")
        employee_name = user_data.get("employee_name") or user_data.get("manual_name")

    # Fallback to persisted agent state
    try:
        from agent_state import (
            load_state_from_file as _load_state,
            is_verified as _is_verified,
            verified_user_name as _v_name,
            verified_user_id as _v_id,
        )  # type: ignore
        _load_state()
        if _is_verified:
            state_verified = True
            if not employee_id:
                employee_id = _v_id
            if not employee_name:
                employee_name = _v_name
    except Exception:
        pass

    verified = (session_verified or state_verified) and bool(employee_id or employee_name)
    return employee_id, employee_name, verified


def _norm(s: str) -> str:
    return "".join(ch.lower() for ch in (s or "") if ch.isalnum())


def _alias_hit(req: str, key: str) -> bool:
    nreq = _norm(req)
    nkey = _norm(key)
    if not nreq or not nkey:
        return False
    if nreq == nkey or nreq in nkey or nkey in nreq:
        return True
    for canon, aliases in FIELD_ALIASES.items():
        if nreq == _norm(canon) or nreq in {_norm(a) for a in aliases}:
            if nkey == _norm(canon) or nkey in {_norm(a) for a in aliases}:
                return True
    return False


def _select_fields(payload: dict, fields: Optional[str]) -> dict:
    if not fields:
        return payload

    requested = [f.strip().lower() for f in fields.split(",") if f.strip()]

    result: dict = {}
    for req in requested:
        for key, value in payload.items():
            if _alias_hit(req, key):
                result[key] = value
    return result


def _ordered_items(raw: dict) -> list[tuple[str, object]]:
    order = [
        "name",
        "employee_id",
        "role",
        "department",
        "date_of_joining",
        "email",
        "phone",
        "location",
        "manager",
        "status",
    ]

    def find_key_for(alias_key: str) -> Optional[str]:
        targets = FIELD_ALIASES.get(alias_key, {alias_key})
        norms = {_norm(t) for t in targets}
        for k in raw.keys():
            nk = _norm(k)
            if nk in norms:
                return k
        for k in raw.keys():
            nk = _norm(k)
            if any(n in nk for n in norms) or any(nk in n for n in norms):
                return k
        return None

    seen: set[str] = set()
    items: list[tuple[str, object]] = []
    for alias in order:
        k = find_key_for(alias)
        if k and k not in seen and raw.get(k) not in (None, ""):
            seen.add(k)
            items.append((k, raw[k]))

    # Append remaining keys not covered
    for k, v in raw.items():
        if k not in seen and v not in (None, ""):
            items.append((k, v))
    return items


def _format_text(name: Optional[str], emp_id: Optional[str], data: dict, *, targeted: bool = False, requested_fields: list[str] | None = None) -> str:
    if not data:
        if targeted and requested_fields:
            pretty = ", ".join(requested_fields)
            return f"I couldn't find your {pretty} in the record."
        return "No matching details found."

    items = _ordered_items(data)

    speakable: list[tuple[str, object]] = []
    for k, v in items:
        nk = _norm(k)
        if nk in {"photourl", "profilephoto", "image", "avatar"}:
            continue
        if nk == "id":
            continue
        if isinstance(v, (list, dict)):
            continue
        if isinstance(v, str) and v.strip().lower().startswith(("http://", "https://")):
            continue
        speakable.append((k, v))

    if targeted or len(speakable) <= 2:
        parts = []
        for k, v in speakable:
            label = k.replace("_", " ").title()
            parts.append(f"Your {label} is {v}.")
        return " ".join(parts)

    lines = ["I'll share your details one by one:"]
    for k, v in speakable:
        label = k.replace("_", " ").title()
        lines.append(f"Your {label} is {v}.")
    return "\n".join(lines)


@function_tool()
async def employee_details(
    context: RunContext,
    fields: str | None = None,
    output: str | None = "text",
) -> str:
    try:
        print(f"🔍 DEBUG: employee_details called with fields={fields}, output={output}")
        
        emp_id, emp_name, verified = _resolve_verified_identity()
        if not verified:
            return "❌ You are not verified yet. Please complete verification to access your details."

        if not emp_id:
            return "❌ Unable to determine your employee ID from the verified session. Please retry verification."

        print(f"🔍 DEBUG: Attempting to get employee data for ID: {emp_id}")
        
        try:
            record = get_employee_by_id(emp_id)
            print(f"🔍 DEBUG: Employee data retrieved: {record is not None}")
        except Exception as e:
            print(f"❌ DEBUG: Database error: {e}")
            record = None
        
        if not record:
            return "❌ I couldn't find your record in our employee directory. Please contact HR or try again."
        
        raw = dict(record.get("raw") or {})
        if not raw:
            raw.update({k: v for k, v in record.items() if k != "raw"})

        def _resolve_manager(payload: dict) -> None:
            manager_keys = [k for k in payload.keys() if _alias_hit("manager", k)]
            for mk in manager_keys:
                val = payload.get(mk)
                if isinstance(val, str):
                    v = val.strip()
                    looks_like_id = ("-" in v and len(v) >= 8) or (len(v) > 8 and v.isalnum())
                    if looks_like_id:
                        mgr = get_employee_by_id(v)
                        if mgr and mgr.get("name"):
                            payload[mk] = mgr["name"]

        _resolve_manager(raw)

        filtered = _select_fields(raw, fields)

        if (output or "text").lower() == "text":
            for key in list(filtered.keys()):
                nk = _norm(key)
                if nk in {"photourl", "profilephoto", "image", "avatar", "id"}:
                    filtered.pop(key, None)

        if (output or "text").lower() == "json":
            payload = {
                "verified": True,
                "employee_id": emp_id,
                "name": emp_name,
                "details": filtered,
            }
            return json.dumps(payload, ensure_ascii=False)

        requested_fields = []
        if fields:
            requested_fields = [f.strip() for f in fields.split(",") if f.strip()]

        return _format_text(emp_name, emp_id, filtered, targeted=bool(fields), requested_fields=requested_fields)
        
    except Exception as e:
        print(f"❌ DEBUG: Critical error in employee_details: {e}")
        import traceback
        traceback.print_exc()
        return "I apologize, there was a technical issue accessing your employee details. Please try again in a moment."
