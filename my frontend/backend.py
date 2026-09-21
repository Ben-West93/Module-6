"""
L11 — Streamlit + FastAPI: Backend
===============================================
Run with:
    uvicorn backend:app --reload --port 8000

An authenticated task API.

Endpoints:
    POST   /auth/register          — create an account, return a token
    POST   /auth/token             — log in, return a token
    GET    /auth/me                — who am I?
    GET    /tasks                  — list the current user's tasks
    POST   /tasks                  — create a task
    PATCH  /tasks/{id}/complete    — mark a task done
    PATCH  /tasks/{id}/uncomplete  — mark a task not done
    DELETE /tasks/{id}             — delete a task

Authentication scheme:
    • The token is base64-encoded JSON: {"sub": "<username>"}
        import base64, json
        payload = json.dumps({"sub": username})
        token = base64.b64encode(payload.encode()).decode()
    • Clients send: Authorization: Bearer <token>
    • FastAPI's HTTPBearer security scheme extracts the token

Data storage:
    • In-memory dicts: USERS, TASKS (username → list of tasks), NEXT_IDS (username → int)
    • No database — restarting the server clears everything
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import base64, json

app = FastAPI(
    title="Task API with Auth",
    description="A small authenticated task manager used by the Streamlit frontend.",
    version="2.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Streamlit runs on a different port (8501) than this API (8000), so the browser
# treats requests as cross-origin. Wide-open CORS is fine for a local demo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# ── In-memory data ────────────────────────────────────────────────────────────
# Plain-text passwords are only acceptable because this is a teaching demo.
USERS: dict[str, str] = {
    "demo": "demo",
}

# username → list of task dicts
TASKS: dict[str, list] = {"demo": []}
# username → next id to hand out (ids restart at 1 per user)
NEXT_IDS: dict[str, int] = {"demo": 1}
# username → account creation timestamp (used by /auth/me)
CREATED_AT: dict[str, str] = {}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


CREATED_AT["demo"] = now_iso()


# ── Models ────────────────────────────────────────────────────────────────────
class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def clean_username(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Username cannot be blank")
        if not all(c.isalnum() or c in "_-." for c in value):
            raise ValueError("Username may only contain letters, digits, _ - and .")
        return value


class RegisterRequest(Credentials):
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(Credentials):
    pass


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be empty or whitespace only")
        return value


class Task(BaseModel):
    id: int
    title: str
    done: bool
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class UserResponse(BaseModel):
    username: str
    created_at: str


# ── Token helpers ─────────────────────────────────────────────────────────────
def credentials_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def make_token(username: str) -> str:
    """Encode {"sub": username} as base64-encoded JSON."""
    payload = json.dumps({"sub": username})
    return base64.b64encode(payload.encode()).decode()


def decode_token(token: str) -> str:
    """Decode a base64 JSON token back into a username.

    Raises 401 for anything that is not a well-formed token: bad base64,
    bad JSON, JSON that isn't an object, or a missing/blank "sub" field.
    """
    try:
        payload = json.loads(base64.b64decode(token).decode())
        username = payload["sub"]
    except (ValueError, TypeError, KeyError, UnicodeDecodeError):
        raise credentials_error("Invalid authentication token")

    if not isinstance(username, str) or not username:
        raise credentials_error("Invalid authentication token")
    return username


# ── Auth dependency ───────────────────────────────────────────────────────────
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Resolve the Bearer token into a known username, or fail with 401."""
    username = decode_token(credentials.credentials)
    if username not in USERS:
        raise credentials_error("Unknown user")
    return username


# ── Data helpers ──────────────────────────────────────────────────────────────
def init_user(username: str) -> None:
    """Make sure a user has a task list and an id counter."""
    TASKS.setdefault(username, [])
    NEXT_IDS.setdefault(username, 1)
    CREATED_AT.setdefault(username, now_iso())


def find_task(username: str, task_id: int) -> dict:
    """Return the user's task or raise 404. Another user's id is also a 404."""
    for task in TASKS.get(username, []):
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


# ── Auth routes ───────────────────────────────────────────────────────────────
@app.post("/auth/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest):
    """Create a new account and return a token so the client can log straight in."""
    if body.username in USERS:
        raise HTTPException(
            status_code=409, detail=f"Username '{body.username}' is already taken"
        )
    USERS[body.username] = body.password
    init_user(body.username)
    return TokenResponse(access_token=make_token(body.username), username=body.username)


@app.post("/auth/token", response_model=TokenResponse)
def login(body: LoginRequest):
    """Exchange username + password for a token."""
    # Same message either way, so responses can't be used to enumerate usernames.
    if USERS.get(body.username) != body.password:
        raise credentials_error("Incorrect username or password")

    init_user(body.username)
    return TokenResponse(access_token=make_token(body.username), username=body.username)


@app.get("/auth/me", response_model=UserResponse)
def me(username: str = Depends(get_current_user)):
    return UserResponse(username=username, created_at=CREATED_AT.get(username, now_iso()))


# ── Task routes ───────────────────────────────────────────────────────────────
@app.get("/tasks", response_model=list[Task])
def get_tasks(username: str = Depends(get_current_user)):
    """Return only the tasks belonging to the authenticated user."""
    return TASKS.get(username, [])


@app.post("/tasks", response_model=Task, status_code=201)
def create_task(body: TaskCreate, username: str = Depends(get_current_user)):
    """Create a task for the authenticated user and return it."""
    task_id = NEXT_IDS.get(username, 1)
    task = {
        "id": task_id,
        "title": body.title,
        "done": False,
        "created_at": now_iso(),
    }
    TASKS.setdefault(username, []).append(task)
    NEXT_IDS[username] = task_id + 1
    return task


@app.patch("/tasks/{task_id}/complete", response_model=Task)
def complete_task(task_id: int, username: str = Depends(get_current_user)):
    """Mark one of the authenticated user's tasks as done."""
    task = find_task(username, task_id)
    task["done"] = True
    return task


@app.patch("/tasks/{task_id}/uncomplete", response_model=Task)
def uncomplete_task(task_id: int, username: str = Depends(get_current_user)):
    """Move a task back to pending."""
    task = find_task(username, task_id)
    task["done"] = False
    return task


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, username: str = Depends(get_current_user)):
    """Delete one of the authenticated user's tasks."""
    task = find_task(username, task_id)
    TASKS[username].remove(task)
    return None


@app.get("/")
def root():
    return {"message": "Backend is running. Visit /docs for interactive API docs."}
