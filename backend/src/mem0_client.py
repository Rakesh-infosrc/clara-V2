import json
import logging
from functools import lru_cache
from typing import Iterable, List, Mapping, MutableMapping, Sequence, Optional

try:
    from mem0 import MemoryClient  # type: ignore
except ImportError:  # pragma: no cover
    MemoryClient = None  # type: ignore

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_client() -> MemoryClient | None:
    try:
        return MemoryClient()
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning("Mem0 client unavailable: %s", exc)
        return None


def add_employee_memory(
    messages: Iterable[Mapping[str, str]],
    user_id: str,
    metadata: Mapping[str, str] | None = None,
    entities: Sequence[str] | None = None,
    custom_categories: Optional[Sequence[Mapping[str, str]]] = None,
    output_format: Optional[str] = None,
) -> bool:
    """Persist a sequence of chat messages for a specific employee."""
    client = _get_client()
    if not client:
        return False

    try:
        payload = list(messages)
        kwargs: dict = {"user_id": user_id}
        if metadata:
            kwargs["metadata"] = dict(metadata)
        if entities:
            kwargs["entities"] = list(entities)
        if custom_categories:
            kwargs["custom_categories"] = list(custom_categories)
        if output_format:
            kwargs["output_format"] = output_format
        try:
            client.add(payload, **kwargs)  # type: ignore
            return True
        except Exception:
            # Fallback: remove optional args not supported by some SDK versions
            fallback_kwargs = {k: v for k, v in kwargs.items() if k not in {"custom_categories", "output_format"}}
            client.add(payload, **fallback_kwargs)  # type: ignore
            return True
    except Exception as exc:  # pragma: no cover - network/service failure
        logger.error("Failed to add Mem0 memory for %s (metadata=%s): %s", user_id, metadata, exc)
        return False


def search_employee_memories(query: str, user_id: str, limit: int = 5) -> List[MutableMapping[str, str]]:
    """Search previously stored memories for an employee."""
    client = _get_client()
    if not client:
        return []

    try:
        response = client.search(
            query,
            filters={"user_id": user_id},
            limit=limit,
        )
    except Exception as exc:  # pragma: no cover - service failure
        logger.error("Failed to search Mem0 memories for %s: %s", user_id, exc)
        return []

    if isinstance(response, dict):
        results = response.get("results", [])
    elif isinstance(response, list):
        results = response
    else:  # pragma: no cover - unexpected response
        logger.debug("Unexpected Mem0 search response: %s", json.dumps(response, default=str))
        results = []

    normalized: List[MutableMapping[str, str]] = []
    for item in results:
        if isinstance(item, MutableMapping):
            normalized.append(item)
        elif isinstance(item, Mapping):
            normalized.append(dict(item))
        elif isinstance(item, str):
            normalized.append({"memory": item})
        else:
            normalized.append({"memory": json.dumps(item, default=str)})
    return normalized


def get_all_employee_memories(user_id: str, limit: int | None = None) -> List[MutableMapping[str, str]]:
    client = _get_client()
    if not client:
        return []
    try:
        results = client.get_all(user_id=user_id)
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to get all Mem0 memories for %s: %s", user_id, exc)
        return []
    if isinstance(results, list):
        return [item if isinstance(item, MutableMapping) else dict(item) if isinstance(item, Mapping) else {"memory": json.dumps(item)} for item in results]
    return []


def update_employee_memory(memory_id: str, new_content: str) -> bool:
    client = _get_client()
    if not client:
        return False
    try:
        try:
            client.update(memory_id, memory=new_content)  # type: ignore
            return True
        except Exception:
            client.update(memory_id, new_content)  # type: ignore
            return True
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to update Mem0 memory %s: %s", memory_id, exc)
        return False


def delete_employee_memory(memory_id: str) -> bool:
    client = _get_client()
    if not client:
        return False
    try:
        client.delete(memory_id)  # type: ignore
        return True
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to delete Mem0 memory %s: %s", memory_id, exc)
        return False
