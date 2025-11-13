from dotenv import load_dotenv
from mem0 import MemoryClient
import logging
import json


load_dotenv()
USER_NAME = "David"
mem0 = MemoryClient()


def add_memory() -> None:
    messages_formatted = [
        {
            "role": "user",
            "content": "I really like Linkin Park.",
        },
        {
            "role": "assistant",
            "content": "That is a good choice.",
        },
        {
            "role": "user",
            "content": "I think so too.",
        },
        {
            "role": "assistant",
            "content": "What is your favorite song by them?",
        },
    ]

    mem0.add(messages_formatted, user_id=USER_NAME)


def get_memory_by_query() -> str:
    query = f"What are {USER_NAME}'s preferences?"
    results = mem0.search(query, filters={"user_id": USER_NAME})

    logging.info("Raw search results: %s", results)

    memories = []
    for result in results:
        if isinstance(result, dict):
            memories.append(
                {
                    "memory": result.get("memory", result),
                    "updated_at": result.get("updated_at"),
                }
            )
        else:
            memories.append({"memory": str(result), "updated_at": None})
    memories_str = json.dumps(memories)
    print(f"Memories: {memories_str}")
    return memories_str


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    add_memory()
    get_memory_by_query()