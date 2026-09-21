# L12 — AI Chat Interface

A Streamlit chat app with streaming responses. It runs with no API key at all
(mock mode) and switches to real OpenAI streaming the moment a key is entered.

## Files

| File | Purpose |
| --- | --- |
| `ai_assistant.py` | The whole app — sidebar, chat history, mock generator, streaming |
| `requirements.txt` | Python dependencies |
| `README.md` | This file |

## Setup

```bash
pip install -r requirements.txt
streamlit run ai_assistant.py
```

The app opens at http://localhost:8501.

## Using it

- **No API key:** leave the sidebar key field blank. Replies come from
  `mock_stream()`, a keyword table covering Python, Streamlit, FastAPI, SQL,
  APIs, errors and greetings, streamed one word at a time.
- **With an API key:** paste an OpenAI key into the sidebar. The app sends the
  system prompt plus the full conversation to the selected model and streams
  the reply back. If the key is rejected, the `openai` package is missing, or
  the network fails, it warns and falls back to mock mode instead of crashing.

Sidebar controls: API key (masked), system prompt, model
(`gpt-4o-mini` / `gpt-4o` / `gpt-3.5-turbo`), a history window slider, a Clear
button that wipes the conversation and re-runs, a live message count, and a
token/cost readout.

## Extras

- **Copy / Regenerate** — every assistant reply has a 📋 toggle that reveals the
  raw text with Streamlit's built-in copy icon; the newest reply also has a 🔄
  button that drops it and streams a fresh answer to the same prompt.
- **Token and cost counter** — the sidebar totals prompt and completion tokens
  with `tiktoken` (falling back to a ~4-chars-per-token estimate if it isn't
  installed) and prices them at the selected model's published rates. The dollar
  figure is an estimate, not a bill.
- **History window** — the slider caps how many recent exchanges are sent to the
  model. The full conversation stays on screen; only the window is transmitted.
- **Avatars and timestamps** — each message stores an `HH:MM` stamp shown under
  the bubble, with distinct user and assistant avatars.
- **Stop button** — appears while a reply streams. Clicking it re-runs the
  script, which halts the generator; the text streamed so far is recovered from
  session state, marked `⏹️ stopped`, and kept in history. A browser refresh
  mid-stream is recovered the same way.

## How the chat history works

Streamlit re-runs the entire script on every interaction, so nothing on screen
survives by itself. Messages are kept in `st.session_state.messages` as
`{"role": ..., "content": ...}` dicts, and a loop redraws all of them with
`st.chat_message()` on each run. New input follows the same cycle: append the
user message, render it, stream the reply with `st.write_stream()` (which
returns the assembled string), then append that string to the history.

## Error handling

- API calls are wrapped in `try/except`; failures warn in the UI and degrade to
  mock mode rather than raising.
- A stream that dies mid-response is caught and replaced with an inline error
  message, and the turn is still stored so history stays consistent.
- Blank or whitespace-only input is ignored.
- The API fallback warning is stored in session state so it survives the re-run
  that ends a turn.
- Token counting degrades to an estimate rather than failing if `tiktoken` is
  missing or its encoding can't be loaded.
- `st.write_stream()` output is normalised to a string before it is stored.

## Testing

Verified with Streamlit's `AppTest` harness across 115 checks: first-run state,
single and multi-turn conversations, history re-rendering without duplication,
the Clear button, whitespace / very long / Unicode / markdown input, sidebar
setting changes, an invalid API key, and a stubbed OpenAI client covering a
normal stream, an empty stream and a stream that raises mid-flight — plus the
copy toggle, repeated regeneration, token/cost totals across models, the
history window actually trimming what is sent, and recovery from an interrupted
stream with and without partial text.
