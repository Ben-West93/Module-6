"""
L6 — Mini Dashboard: FastAPI Backend
=================================================
Run this server:
    uvicorn mini_api:app --reload --port 8000

A small task API backed by a Python list, persisted to a JSON file so the
data survives a restart (including uvicorn's --reload).

Endpoints:
    GET    /tasks                 — return all tasks
    POST   /tasks                 — create a task            (body: {"title": "..."})
    PATCH  /tasks/{id}/complete   — mark a task done
    PATCH  /tasks/{id}            — update a task            (body: {"done": true|false})
    DELETE /tasks/{id}            — delete a task            (204, no body)

Key concepts:
    • CORSMiddleware — lets browsers on a different origin (port) call this API
    • Pydantic BaseModel — validates request bodies and, via response_model,
      documents and filters the response shape in /docs
    • HTTPException — returns an HTTP error with a given status code
    • JSON-file persistence — simple durable storage without a real database
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Mini Task API")

# ── CORS ─────────────────────────────────────────────────────────────────────
# Without this, browsers block JavaScript served from http://localhost:5500
# from calling an API on http://localhost:8000 (different port = different origin).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ──────────────────────────────────────────────────────────────────
class Task(BaseModel):
    """The shape of a task as the API returns it."""
    id: int
    title: str
    done: bool
    created_at: str


class TaskCreate(BaseModel):
    """Body for POST /tasks."""
    title: str = Field(min_length=1)


class TaskUpdate(BaseModel):
    """Body for PATCH /tasks/{id}. Every field is optional — send only what changes."""
    title: Optional[str] = Field(default=None, min_length=1)
    done: Optional[bool] = None


# ── Storage ──────────────────────────────────────────────────────────────────
DATA_FILE = Path(__file__).with_name("tasks.json")

SEED_TASKS = [
    {"id": 1, "title": "Read the FastAPI docs", "done": True, "created_at": "2026-03-01"},
    {"id": 2, "title": "Build the mini dashboard", "done": False, "created_at": "2026-03-02"},
    {"id": 3, "title": "Test every endpoint", "done": False, "created_at": "2026-03-02"},
]


def load_tasks() -> List[dict]:
    """Read tasks from disk, falling back to the seed list on a missing or bad file."""
    if not DATA_FILE.exists():
        return [dict(task) for task in SEED_TASKS]

    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # A corrupt or unreadable file should not take the API down.
        return [dict(task) for task in SEED_TASKS]

    if not isinstance(data, list):
        return [dict(task) for task in SEED_TASKS]

    # Keep only entries that actually look like tasks.
    return [
        item for item in data
        if isinstance(item, dict) and {"id", "title", "done", "created_at"} <= set(item)
    ]


def save_tasks() -> None:
    """Write the current list to disk. A write error must not break a request."""
    try:
        DATA_FILE.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
    except OSError as error:
        print(f"[warn] could not save tasks: {error}")


tasks: List[dict] = load_tasks()
next_id: int = max((task["id"] for task in tasks), default=0) + 1


def find_task(task_id: int) -> dict:
    """Return the task with this id, or raise a 404."""
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found.")


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/tasks", response_model=List[Task])
def get_tasks():
    """Return every task."""
    return tasks


@app.post("/tasks", response_model=Task, status_code=201)
def create_task(body: TaskCreate):
    """Create a task and return it."""
    global next_id

    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Title must not be empty.")

    task = {
        "id": next_id,
        "title": title,
        "done": False,
        "created_at": datetime.now().strftime("%Y-%m-%d"),
    }
    tasks.append(task)
    next_id += 1
    save_tasks()
    return task


@app.patch("/tasks/{task_id}/complete", response_model=Task)
def complete_task(task_id: int):
    """Mark a task done. Its own route for the simple one-click case."""
    task = find_task(task_id)
    task["done"] = True
    save_tasks()
    return task


@app.patch("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, body: TaskUpdate):
    """Update a task. Send {"done": false} to un-complete it, or a new title."""
    task = find_task(task_id)

    if body.done is None and body.title is None:
        raise HTTPException(status_code=422, detail="Provide at least one field to update.")

    if body.title is not None:
        title = body.title.strip()
        if not title:
            raise HTTPException(status_code=422, detail="Title must not be empty.")
        task["title"] = title

    if body.done is not None:
        task["done"] = body.done

    save_tasks()
    return task


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    """Delete a task. Returns 204 with no body."""
    task = find_task(task_id)
    tasks.remove(task)
    save_tasks()
    return Response(status_code=204)


@app.get("/")
def root():
    return {"message": "Mini Task API is running. Visit /docs for interactive docs."}
