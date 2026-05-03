# LLM Chat

A simple LLM chat interface built as a technical assessment. It streams responses token-by-token from the Gemini API and persists full conversation history in SQLite.

---

## Architecture

```
maistorage_assessment/
├── backend/          # Python · FastAPI · SQLAlchemy · google-genai
└── frontend/         # Next.js 14 · TypeScript · Tailwind CSS
```

### Backend

| Layer | Technology |
|---|---|
| API framework | FastAPI (async) |
| Streaming | Server-Sent Events (SSE) via `StreamingResponse` |
| LLM | Google Gemini (`google-genai` SDK) |
| Database | SQLite via SQLAlchemy 2 async + aiosqlite |
| Config | pydantic-settings (`.env`) |
| Tests | pytest + pytest-asyncio |

---

#### Why FastAPI?

The core requirement is streaming tokens to the browser as they arrive. FastAPI supports `StreamingResponse` natively and is built on ASGI (async), which means the server does not block a thread while waiting for each chunk from the Gemini API. A synchronous framework (Flask, Django) would hold a thread open for the full duration of every streaming request, making it poorly suited for this workload.

---

#### Module structure — why schema → repository → service → router?

```
app/
├── core/
│   ├── config.py       # Settings (pydantic-settings)
│   └── gemini.py       # Gemini client factory
├── models/
│   ├── session.py      # Session ORM model
│   └── message.py      # Message ORM model (role, content, token usage)
├── modules/
│   ├── sessions/       # schemas · repository · service · router
│   └── chat/           # schemas · repository · service · router
├── database.py         # Async engine + get_db dependency
└── main.py             # App factory, CORS, lifespan (table creation)
```

Each domain module (`sessions`, `chat`) has exactly four files:

| File | Responsibility | Why it exists separately |
|---|---|---|
| `schemas.py` | Pydantic DTOs for request/response | Decouples the HTTP contract from the database model. The ORM shape and the API shape are not always the same — e.g. `SessionListItem` adds `message_count` which is not a column. |
| `repository.py` | All SQLAlchemy queries | Centralises every DB access for a domain in one place. If the query logic needs to change (e.g. add an index, change ordering) there is exactly one file to touch. The service never writes raw SQL or ORM queries. |
| `service.py` | Business logic | The only layer that makes decisions: input validation, orchestration across repositories, HTTP error raising. Keeping this separate from the router means the logic can be tested without an HTTP request, and without a real database. |
| `router.py` | HTTP wiring only | Maps URL + method to a service call, declares response models. It contains no business logic — just dependency resolution and delegation. |

The strict layering means you can answer "where is the query that fetches messages?" (repository), "where is the check that a session exists?" (service), and "what does the API return?" (schemas) without reading the whole codebase.

---

#### Why dependency injection?

**At the router layer**, FastAPI's `Depends` is used to build the service:

```python
def _get_service(db: AsyncSession = Depends(get_db)) -> SessionService:
    return SessionService(db)

@router.get("/")
async def list_sessions(service: SessionService = Depends(_get_service)):
    ...
```

This means the database session is created by FastAPI per-request and automatically closed after the response — the router never manages connection lifecycle manually.

**At the service layer**, repositories are injected via the constructor with a default fallback:

```python
class SessionService:
    def __init__(self, db: AsyncSession, repository: Optional[SessionRepository] = None):
        self.repository = repository or SessionRepository(db)
```

The `Optional` parameter is the **test seam**. In production, callers just pass `db` and the real repository is created automatically. In tests, a mock is injected instead:

```python
service = SessionService(db=MagicMock(), repository=mock_repo)
```

This makes it possible to test all business logic — including error paths — without a real database, without migrations, and without async test fixtures for SQLite. Tests are fast and deterministic.

---

#### Why SQLAlchemy 2 async instead of a lighter ORM?

SQLAlchemy 2's async API (`AsyncSession`, `create_async_engine`) integrates correctly with Python's `asyncio` event loop. A synchronous ORM would block the event loop on every query, defeating the purpose of using an async framework. The ORM also handles cascade deletes (deleting a session removes all its messages) declaratively via `relationship(..., cascade="all, delete-orphan")`, without needing a manual delete query.

---

#### Why SQLite?

The requirement specifies simple session management. SQLite requires zero infrastructure — no separate database container, no connection pooling configuration, no credentials. The async driver (`aiosqlite`) wraps SQLite's synchronous file I/O in a thread pool so it does not block the event loop. In Docker, the database file lives in a named volume (`db_data`) so it persists across container restarts.

---

#### Streaming design — why SSE over WebSockets?

Server-Sent Events (SSE) are unidirectional (server → client), which is exactly what streaming LLM output requires. The connection is a plain HTTP response that stays open. Compared to WebSockets:

- No upgrade handshake
- Works through HTTP proxies and load balancers without configuration
- Automatic reconnect is built into the browser's `EventSource` API
- No need for a stateful connection on the server

`POST /chat/stream` returns a `StreamingResponse`. The generator emits three event types:

```
event: token          ← one per chunk from Gemini, streamed immediately
data: {"token": "..."}

event: done           ← emitted once after the full response is saved to DB
data: {"message_id": "...", "usage": {"prompt_tokens": N, "completion_tokens": N, "total_tokens": N}}

event: error          ← emitted if the Gemini API call fails mid-stream
data: {"error": "..."}
```

**Why the generator opens its own DB session:** FastAPI's `Depends(get_db)` session is closed when the response *headers* are sent — which happens before the body finishes streaming. If the generator tried to use the dependency-injected session to save the completed assistant message, the session would already be closed. The generator therefore opens an independent `AsyncSessionLocal()` that it fully controls and that lives for the entire stream duration.

**Why the session is validated before the stream starts:** If the session ID does not exist, the API should return a proper `404 JSON` response — not start an SSE stream and then error inside it. The pre-flight check uses the dependency-injected session (which is valid at that point) to do the validation synchronously before `StreamingResponse` is returned.

---

#### Why pydantic-settings for config?

All configuration (`GEMINI_API_KEY`, `DATABASE_URL`, `CORS_ORIGINS`) is read from environment variables at startup. `pydantic-settings` validates that required fields are present and have the right types before the app starts — rather than failing at runtime when the first request hits a code path that needs them. The `CORS_ORIGINS` field is typed as `str` (not `List[str]`) because pydantic-settings tries to `json.loads()` list fields from env, which fails for a bare URL like `http://localhost:3000`. Splitting is done explicitly at the usage site instead.

### Frontend

| Concern | Detail |
|---|---|
| Framework | Next.js 14 App Router |
| Styling | Tailwind CSS (muted slate palette) + `@tailwindcss/typography` |
| Markdown | `react-markdown` + `remark-gfm` |
| Math equations | `remark-math` + `rehype-katex` + KaTeX CSS |
| Streaming | Native `fetch` + `ReadableStream` SSE parser |
| State | `useChat` hook — optimistic updates, abort controller |

Sessions are **auto-named** from the first 50 characters of the user's opening message.

---

## Running locally

### Prerequisites

- Python 3.12+
- Node.js 20+
- A [Gemini API key](https://aistudio.google.com/app/apikey)

### Backend

```bash
cd backend
cp .env.example .env          # fill in GEMINI_API_KEY
pip install -r requirements.txt
uvicorn app.main:app --reload
# → http://localhost:8000
```

### Frontend

```bash
cd frontend
cp .env.example .env.local    # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev
# → http://localhost:3000
```

---

## Running with Docker

```bash
cp .env.example .env          # fill in GEMINI_API_KEY
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |

SQLite data is persisted in the `db_data` Docker volume.

> The backend container runs `pytest -v` on startup and will **not start the server** if any test fails.

---

## API reference

### Sessions

| Method | Path | Description |
|---|---|---|
| `GET` | `/sessions/` | List all sessions |
| `POST` | `/sessions/` | Create a session |
| `GET` | `/sessions/{id}` | Get a session |
| `DELETE` | `/sessions/{id}` | Delete a session (cascades messages) |

### Chat

| Method | Path | Description |
|---|---|---|
| `POST` | `/chat/stream` | Stream a response (SSE) |
| `GET` | `/chat/sessions/{id}/messages` | Get full message history |

---

## Tests

Unit tests cover the service layer with mocked repositories — no database or network required.

```bash
cd backend
pytest -v
```

| File | What is tested |
|---|---|
| `tests/test_sessions_service.py` | create (success, whitespace trim, empty name 422), get_all, get_by_id (found / 404), delete (success / 404) |
| `tests/test_chat_service.py` | `build_gemini_contents` (no history, ordering, role mapping), `get_history` (session 404, returns messages), `validate_session` (404 / passes) |

### Testing methodology

#### Why unit tests only (for the service layer)?

The business logic lives in the service layer. That is where decisions are made: whether to raise a 404, whether to reject an empty name, how to map history into Gemini's content format. Testing at this layer gives the highest confidence-to-cost ratio:

- No real database — no migrations, no test fixtures, no async SQLite setup
- No real Gemini API — no API key, no network, no flaky external dependency
- Tests complete in milliseconds
- Failures point directly at the logic that broke, not at infrastructure

The repository and router layers are intentionally not unit-tested here because:
- The **repository** is thin wrappers around SQLAlchemy queries. Its correctness is best verified by integration tests against a real DB, which are out of scope for this assessment.
- The **router** contains no logic — just `Depends` resolution and delegation. Testing it would only test FastAPI's own DI mechanism.

#### How mock injection works

Both service classes accept an optional repository argument:

```python
class SessionService:
    def __init__(self, db: AsyncSession, repository: Optional[SessionRepository] = None):
        self.repository = repository or SessionRepository(db)
```

In tests, an `AsyncMock` is passed in place of the real repository. `AsyncMock` automatically makes every method an awaitable that returns a configurable value:

```python
mock_repo = AsyncMock()
mock_repo.get_by_id.return_value = None   # simulate "not found"

service = SessionService(db=MagicMock(), repository=mock_repo)

with pytest.raises(HTTPException) as exc_info:
    await service.get_by_id("nonexistent")

assert exc_info.value.status_code == 404
mock_repo.get_by_id.assert_called_once_with("nonexistent")  # verify it was called correctly
```

This pattern tests three things in one assertion block:
1. The service calls the repository with the right arguments
2. The service reacts correctly to the repository's return value
3. The service raises the right HTTP error

#### What `build_gemini_contents` tests verify

`build_gemini_contents` is a pure function (no async, no DB, no side effects) that converts stored `Message` objects into Gemini's `contents` format. It is tested exhaustively because it is the function that determines what context the model sees:

- Empty history — verifies the new message is the only entry and has `role: user`
- Ordering — verifies history is preserved in chronological order
- Role mapping — verifies `assistant` is converted to `model` (Gemini's required role name)
- New message is always last — verifies the current user turn is appended after history

A bug in this function would silently corrupt the conversation context sent to the model, making it the most important pure logic to test precisely.

#### Why `pytest-asyncio` with `asyncio_mode = auto`?

All service methods are `async def`. `pytest-asyncio` runs them inside an event loop. `asyncio_mode = auto` (set in `pytest.ini`) means every `async def test_*` function is automatically treated as an async test — no `@pytest.mark.asyncio` decorator needed on each test.