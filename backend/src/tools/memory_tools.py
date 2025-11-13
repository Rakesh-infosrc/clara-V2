import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Sequence, List, Dict, Any

from livekit.agents import function_tool, RunContext

from mem0_client import (
    add_employee_memory,
    get_all_employee_memories,
    update_employee_memory,
    delete_employee_memory,
    search_employee_memories,
)


try:
    from dateutil import parser as _dtparser
except Exception:  # pragma: no cover - optional dependency
    _dtparser = None


def _normalize_reminder_time(reminder_time: str) -> Optional[str]:
    if not reminder_time:
        return None
    reminder_time = reminder_time.strip()
    if not reminder_time:
        return None
    try:
        dt = datetime.fromisoformat(reminder_time)
    except Exception:
        if not _dtparser:
            return None
        try:
            dt = _dtparser.parse(reminder_time, fuzzy=True)
        except Exception:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt_utc = dt.astimezone(timezone.utc)
    if dt_utc < datetime.now(timezone.utc) - timedelta(minutes=1):
        return None
    return dt_utc.isoformat()


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        try:
            if _dtparser:
                dt = _dtparser.parse(value)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
        except Exception:
            return None
    return None


def _resolve_mem_identity() -> tuple[Optional[str], Optional[str], Optional[Dict[str, str]]]:
    """Resolve verified identity for Mem0 tools from flow session and agent state."""
    employee_id: Optional[str] = None
    employee_name: Optional[str] = None

    # Prefer flow session when available
    try:
        from flow_manager import flow_manager  # type: ignore
        session = flow_manager.get_current_session()
    except Exception:
        session = None

    if session and getattr(session, "is_verified", False):
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
            if not employee_id:
                employee_id = _v_id
            if not employee_name:
                employee_name = _v_name
    except Exception:
        pass

    if not employee_id and not employee_name:
        return None, None, None

    if employee_id and employee_name:
        mem_user_id = f"{employee_id}:{employee_name}"
    else:
        mem_user_id = employee_id or employee_name
    metadata = {
        "employee_id": employee_id or "",
        "employee_name": employee_name or "",
    }
    return mem_user_id, employee_name, metadata


@function_tool()
async def memory_add(
    context: RunContext,  # type: ignore
    information: str,
    categories: Optional[str] = None,
    custom_categories: Optional[str] = None,
    output_format: Optional[str] = None,
    reminder_time: Optional[str] = None,
    reminder: Optional[bool] = None,
) -> str:
    """Add a memory item for the verified employee. Uses employee name as Mem0 ENTITIES.

    Args:
        information: The information to store
        categories: Optional comma-separated categories/tags
    """
    mem_user_id, employee_name, meta = _resolve_mem_identity()
    if not mem_user_id:
        return "Please verify your identity first. Say 'Hey Clara' to start the verification process."

    metadata = dict(meta or {})
    if categories:
        metadata["categories"] = categories
    metadata.setdefault("type", "explicit_memory")
    metadata["detail"] = information

    reminder_iso: Optional[str] = None
    if reminder_time:
        reminder_iso = _normalize_reminder_time(reminder_time)
        if not reminder_iso:
            return "⚠️ I couldn't understand that reminder time. Please use a format like '2025-11-12 14:30' or 'tomorrow at 5pm'."
        metadata["type"] = "reminder"
        metadata["reminder_time"] = reminder_iso
        existing = metadata.get("categories")
        if existing:
            metadata["categories"] = f"{existing},reminder"
        else:
            metadata["categories"] = "reminder"

    if reminder:
        metadata["type"] = "reminder"
        existing = metadata.get("categories")
        if existing and "reminder" not in existing:
            metadata["categories"] = f"{existing},reminder"
        elif not existing:
            metadata["categories"] = "reminder"

    payload = [
        {"role": "user", "content": information},
        {
            "role": "assistant",
            "content": (
                f"Reminder scheduled: {information}"
                if metadata.get("type") == "reminder"
                else f"Noted: {information}"
            ),
        },
    ]

    cc = None
    if custom_categories:
        try:
            parsed = json.loads(custom_categories)
            if isinstance(parsed, list):
                cc = [dict(item) for item in parsed if isinstance(item, dict)]
            elif isinstance(parsed, dict):
                cc = [dict(parsed)]
        except Exception:
            cc = None

    if cc is None:
        if metadata.get("type") == "reminder":
            cc = [
                {"reminder": "Time-based reminders"},
                {"schedule": "Schedule and meetings"},
            ]
            try:
                if reminder_iso:
                    dt = _parse_iso_datetime(reminder_iso)
                    now_d = datetime.now(timezone.utc).date()
                    if dt and dt.date() == now_d:
                        cc.append({"today": "Today's reminders"})
                        existing = metadata.get("categories")
                        if existing:
                            if "today" not in existing:
                                metadata["categories"] = f"{existing},today"
                        else:
                            metadata["categories"] = "today"
            except Exception:
                pass
        else:
            cc = [{"notes": "Personal notes"}]

    ok = add_employee_memory(
        payload,
        user_id=mem_user_id,
        metadata=metadata,
        entities=[employee_name] if employee_name else None,
        custom_categories=cc,
        output_format=output_format,
    )
    if metadata.get("type") == "reminder":
        if not ok:
            return "⚠️ I couldn't save that reminder right now. Please try again later."
        if not reminder_iso:
            return "✅ Reminder saved."
        friendly_dt = _parse_iso_datetime(reminder_iso)
        friendly_text = friendly_dt.strftime("%Y-%m-%d %H:%M UTC") if friendly_dt else reminder_iso
        return f"✅ Reminder set for {friendly_text}."
    return "✅ Saved to your private memory." if ok else "⚠️ I couldn't save that right now. Please try again later."


@function_tool()
async def memory_get_all(
    context: RunContext,  # type: ignore
    limit: int = 20,
) -> str:
    """Get all memory items for the verified employee (private scope)."""
    mem_user_id, employee_name, _ = _resolve_mem_identity()
    if not mem_user_id:
        return "Please verify your identity first. Say 'Hey Clara' to start the verification process."

    items = get_all_employee_memories(mem_user_id)
    if not items:
        return "No memories found for your profile."

    lines: List[str] = []
    for i, it in enumerate(items[: max(1, limit) ]):
        mem = it.get("memory") if isinstance(it, dict) else str(it)
        ts = it.get("updated_at") if isinstance(it, dict) else None
        _id = it.get("id") if isinstance(it, dict) else None
        piece = mem if isinstance(mem, str) else str(mem)
        if ts:
            lines.append(f"- {_id or i+1}: {piece} (updated {ts})")
        else:
            lines.append(f"- {_id or i+1}: {piece}")

    header = f"Here are your memories, {employee_name}:" if employee_name else "Here are your memories:"
    return "\n".join([header, *lines])


@function_tool()
async def memory_update(
    context: RunContext,  # type: ignore
    memory_id: str,
    content: str,
) -> str:
    """Update an existing memory for the verified employee (by memory_id)."""
    mem_user_id, _, _ = _resolve_mem_identity()
    if not mem_user_id:
        return "Please verify your identity first. Say 'Hey Clara' to start the verification process."

    ok = update_employee_memory(memory_id, content)
    return "✅ Memory updated." if ok else "⚠️ Failed to update memory."


@function_tool()
async def memory_delete(
    context: RunContext,  # type: ignore
    memory_id: str,
) -> str:
    """Delete a memory by id for the verified employee."""
    mem_user_id, _, _ = _resolve_mem_identity()
    if not mem_user_id:
        return "Please verify your identity first. Say 'Hey Clara' to start the verification process."

    ok = delete_employee_memory(memory_id)
    return "🗑️ Memory deleted." if ok else "⚠️ Failed to delete memory."


@function_tool()
async def memory_recall(
    context: RunContext,  # type: ignore
    query: str,
    limit: int = 5,
) -> str:
    mem_user_id, employee_name, _ = _resolve_mem_identity()
    if not mem_user_id:
        return "Please verify your identity first. Say 'Hey Clara' to start the verification process."

    lowered = (query or "").strip().lower()

    if any(k in lowered for k in ("today", "today's", "call today", "meeting today")):
        all_items = get_all_employee_memories(mem_user_id)
        if not all_items:
            return "No reminders for today."
        now_d = datetime.now(timezone.utc).date()
        picked: List[str] = []
        for it in all_items:
            if not isinstance(it, dict):
                continue
            md = it.get("metadata")
            if not isinstance(md, dict):
                continue
            if md.get("type") != "reminder":
                continue
            dt = _parse_iso_datetime(md.get("reminder_time"))
            if not dt or dt.date() != now_d:
                continue
            detail = md.get("detail") if isinstance(md.get("detail"), str) else None
            if not detail:
                mem = it.get("memory")
                detail = mem if isinstance(mem, str) else json.dumps(mem, ensure_ascii=False)
            picked.append(f"{dt.strftime('%H:%M')}: {detail}")
        return "\n".join(picked) if picked else "No reminders for today."

    items = search_employee_memories(query, mem_user_id, limit=limit * 2)
    if not items:
        return "I couldn't find anything relevant in your memories."

    summaries: List[str] = []
    for it in items:
        if not isinstance(it, dict):
            summaries.append(str(it))
            continue
        md = it.get("metadata") if isinstance(it.get("metadata"), dict) else None
        detail = (md or {}).get("detail") if md else None
        if isinstance(detail, str) and detail.strip():
            summaries.append(detail.strip())
        else:
            mem = it.get("memory")
            if isinstance(mem, str):
                summaries.append(mem)
            else:
                summaries.append(json.dumps(mem, ensure_ascii=False))
        if len(summaries) >= max(1, limit):
            break

    return "\n".join(summaries)


@function_tool()
async def memory_list_reminders(
    context: RunContext,  # type: ignore
    within_hours: int = 168,
    include_overdue: bool = True,
) -> str:
    """List upcoming reminders stored for the verified employee."""

    mem_user_id, employee_name, _ = _resolve_mem_identity()
    if not mem_user_id:
        return "Please verify your identity first. Say 'Hey Clara' to start the verification process."

    items = get_all_employee_memories(mem_user_id)
    if not items:
        return "There are no reminders saved yet."

    now = datetime.now(timezone.utc)
    horizon = now + timedelta(hours=max(1, within_hours))

    reminders: List[tuple[datetime, Dict[str, Any]]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata")
        if not isinstance(metadata, dict):
            continue
        if metadata.get("type") != "reminder":
            continue
        r_time = _parse_iso_datetime(metadata.get("reminder_time"))
        if not r_time:
            continue
        if include_overdue and r_time <= now:
            reminders.append((r_time, item))
        elif now < r_time <= horizon:
            reminders.append((r_time, item))

    if not reminders:
        return "No reminders due in that time window."

    reminders.sort(key=lambda pair: pair[0])
    lines = []
    for dt_obj, item in reminders:
        md = item.get("metadata") if isinstance(item.get("metadata"), dict) else None
        detail = (md or {}).get("detail") if md else None
        if isinstance(detail, str) and detail.strip():
            text = detail.strip()
        else:
            memory_text = item.get("memory") if isinstance(item.get("memory"), str) else item.get("memory")
            if not isinstance(memory_text, str):
                text = json.dumps(memory_text, ensure_ascii=False)
            else:
                text = memory_text
        human_time = dt_obj.strftime("%H:%M")
        lines.append(f"{human_time}: {text}")

    return "\n".join(lines)
