"""
Module 6 Project - AI Dashboard
FastAPI Backend
===============
Run with:
    uvicorn backend:app --reload --port 8000

Interactive docs while it runs: http://localhost:8000/docs

Serves exactly the four endpoints api_client.py calls, and nothing else:

    POST   /auth/token              -> {"access_token": "...", "token_type": "bearer"}
    GET    /tasks                   -> [task, ...]
    POST   /tasks                   -> the created task (201)
    PATCH  /tasks/{task_id}/complete-> the updated task

Demo accounts (see USERS below):
    demo_user / demo1234
    ben       / module6

Scope and limitations
---------------------
This is a teaching backend, deliberately kept to one file:

  * Storage is an in-memory dict. Restarting uvicorn resets every task back to
    the seed data, and `--reload` will do the same on each code change.
  * Passwords are PBKDF2-HMAC-SHA256 hashes generated at import time from the
    plaintext in USERS, so the demo credentials stay readable in the source.
    A real service would store only the hash, created by a library such as
    passlib/bcrypt, and would never hold the plaintext at all.
  * The signing key is a hard-coded constant. In production it would come from
    the environment (or .streamlit/secrets.toml on the client side) and would
    never be committed.
  * /auth/token takes a JSON body rather than the OAuth2 form encoding, because
    that is what api_client.login() sends. FastAPI's OAuth2PasswordRequestForm
    would expect form fields instead.

Tasks are stored per user, so two accounts do not see each other's data.
"""

import hashlib
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

# ── Configuration ──────────────────────────────────────────────────────────
# Demo defaults; override with environment variables when running for real.
# At least 32 bytes: PyJWT warns about shorter HMAC keys for HS256 (RFC 7518).
SECRET_KEY = os.getenv("AI_DASHBOARD_SECRET", "dev-only-secret-change-me-before-you-deploy")
ALGORITHM = "HS256"
# Set AI_DASHBOARD_TOKEN_MINUTES=1 to watch the dashboard's auto-logout kick in.
TOKEN_TTL_MINUTES = int(os.getenv("AI_DASHBOARD_TOKEN_MINUTES", "60"))

# Fixed salt so the demo hashes are reproducible. A real system salts per user.
PASSWORD_SALT = b"module6-demo-salt"


def hash_password(plaintext: str) -> str:
    """PBKDF2-SHA256 hash. Stdlib only - no bcrypt dependency for a demo."""
    return hashlib.pbkdf2_hmac(
        "sha256", plaintext.encode("utf-8"), PASSWORD_SALT, 100_000
    ).hex()


# username -> password hash. Plaintext is hashed once at import.
USERS = {
    "demo_user": hash_password("demo1234"),
    "ben": hash_password("module6"),
}

# username -> list of task dicts. Seeded so a fresh login is not an empty page.
TASKS: dict[str, list[dict]] = {}
NEXT_ID = {"value": 1}


def seed_tasks() -> list[dict]:
    """Starter tasks handed to a user the first time they log in."""
    starter = [
        ("Complete the AI Dashboard project", False),
        ("Review FastAPI authentication notes", True),
        ("Practice CSS Flexbox layouts", False),
    ]
    created = []
    for title, done in starter:
        created.append(
            {
                "id": NEXT_ID["value"],
                "title": title,
                "done": done,
                "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            }
        )
        NEXT_ID["value"] += 1
    return created


def tasks_for(username: str) -> list[dict]:
    """Return this user's task list, seeding it on first access."""
    if username not in TASKS:
        TASKS[username] = seed_tasks()
    return TASKS[username]


# ── Schemas ────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class Task(BaseModel):
    id: int
    title: str
    done: bool
    created_at: str


# ── App ────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Dashboard API",
    version="1.0.0",
    description="Minimal task API backing the Module 6 Streamlit dashboard.",
)


def create_access_token(username: str) -> str:
    """Sign a JWT whose subject is the username and which expires in TOKEN_TTL_MINUTES."""
    payload = {
        "sub": username,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=TOKEN_TTL_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def current_user(authorization: str = Header(default=None)) -> str:
    """
    Dependency that turns an Authorization header into a username.

    Every failure path returns 401 with a readable detail, because that is the
    status api_client treats as "session expired" and the dashboard reacts to
    by logging the user out.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is not valid.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload.get("sub")
    if username not in USERS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unknown user.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username


@app.post("/auth/token", response_model=TokenResponse)
def login(body: LoginRequest):
    """Exchange username + password for a JWT."""
    expected = USERS.get(body.username)
    # hmac-style constant work either way: always hash, then compare.
    supplied = hash_password(body.password)
    if expected is None or supplied != expected:
        # One message for both cases - do not reveal which usernames exist.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
        )
    return TokenResponse(access_token=create_access_token(body.username))


@app.get("/tasks", response_model=list[Task])
def list_tasks(username: str = Depends(current_user)):
    """Every task belonging to the authenticated user."""
    return tasks_for(username)


@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(body: TaskCreate, username: str = Depends(current_user)):
    """Add a task. The title is stored exactly as sent, minus outer whitespace."""
    title = body.title.strip()
    if not title:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Task title cannot be blank.",
        )

    task = {
        "id": NEXT_ID["value"],
        "title": title,
        "done": False,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    NEXT_ID["value"] += 1
    tasks_for(username).append(task)
    return task


@app.patch("/tasks/{task_id}/complete", response_model=Task)
def complete_task(task_id: int, username: str = Depends(current_user)):
    """
    Mark a task done and return it.

    Completing an already-completed task is not an error - the end state is the
    same, so the call is idempotent.
    """
    for task in tasks_for(username):
        if task["id"] == task_id:
            task["done"] = True
            return task

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task {task_id} not found.",
    )


@app.get("/health")
def health():
    """Unauthenticated liveness check, handy for confirming the port is up."""
    return {"status": "ok"}
