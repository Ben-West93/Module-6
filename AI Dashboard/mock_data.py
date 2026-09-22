"""
Module 6 Project — AI Dashboard  (STARTER)
Mock Data for Offline Development
===================================
Use these constants when the backend isn't running so you can build
and test the UI without a live API connection.
"""

MOCK_TOKEN = "mock-token-for-offline-development"

MOCK_USER = "demo_user"

MOCK_TASKS = [
    {"id": 1, "title": "Complete the AI Dashboard project",    "done": False, "created_at": "2026-03-10"},
    {"id": 2, "title": "Review FastAPI authentication notes",  "done": True,  "created_at": "2026-03-09"},
    {"id": 3, "title": "Practice CSS Flexbox layouts",         "done": False, "created_at": "2026-03-08"},
    {"id": 4, "title": "Read the Streamlit session state docs","done": True,  "created_at": "2026-03-07"},
    {"id": 5, "title": "Watch the REST API lecture recording",  "done": False, "created_at": "2026-03-06"},
]

MOCK_STATS = {
    "total_tasks": len(MOCK_TASKS),
    "done_tasks":  sum(1 for t in MOCK_TASKS if t["done"]),
    "pending_tasks": sum(1 for t in MOCK_TASKS if not t["done"]),
}

MOCK_CHAT_HISTORY = [
    {"role": "user",      "content": "What is FastAPI?"},
    {"role": "assistant", "content": "FastAPI is a modern Python web framework for building APIs. It uses type hints and Pydantic for automatic request validation."},
]
