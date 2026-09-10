r"""
my-ai — web interface (3RROR).

Local:  .\.venv\Scripts\python.exe web.py   ->  http://localhost:5000
Shared: deploy with gunicorn (see README "Put it online").

Endpoints:
  "/"           -> the chat web page (index.html)
  "/config"     -> models + personas the page should offer
  "/chat"       -> streams a reply; optional live web search + persona
  "/transcribe" -> voice clip -> text (Groq Whisper)
  "/healthz"    -> "ok" (for uptime checks)

Conversation history lives in the browser, so this server stays stateless.

--- Sharing controls (set these as environment variables when you deploy) ---
  GROQ_API_KEY     required
  APP_PASSWORD     if set, visitors must enter this once (shared password)
  ALLOW_SEARCH     "false" to disable the web-search button for everyone
  MAX_REPLY_TOKENS cap on reply length (default 800)
  RATE_CHAT        per-visitor chat limit (default "15 per minute;250 per day")
  RATE_VOICE       per-visitor transcribe limit (default "10 per minute;120 per day")
Every visitor shares your one Groq key and its free rate limits.
"""

import json
import os

from dotenv import load_dotenv
from flask import Flask, request, Response, jsonify, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from groq import Groq, AuthenticationError, RateLimitError, APIStatusError, APIConnectionError

# ---- personalities the picker offers -------------------------------------
_BASE = ("Use Markdown when it helps (code blocks, lists, bold). "
         "When you are not sure, say so.")
PERSONAS = {
    "assistant": ("Assistant",
        "You are 3RROR, a friendly, concise personal assistant. Explain things "
        "simply and warmly. " + _BASE),
    "engineer": ("Engineer",
        "You are 3RROR in engineer mode. Terse and precise, code first. Assume "
        "the user is technical. Prefer working code and concrete steps over prose. " + _BASE),
    "tutor": ("Tutor",
        "You are 3RROR in tutor mode. Teach from first principles, one step at a "
        "time. Use analogies and tiny examples, and check understanding as you go. " + _BASE),
    "brainstorm": ("Brainstorm",
        "You are 3RROR in brainstorm mode. Generate many ideas fast, defer "
        "judgement, build on the user's direction, and be bold and playful. " + _BASE),
    "advocate": ("Devil's Advocate",
        "You are 3RROR in devil's-advocate mode. Respectfully challenge the "
        "user's assumptions, surface risks and counter-arguments, and steelman "
        "the opposing view before giving your take. " + _BASE),
    "briefing": ("Briefing",
        "You are 3RROR in briefing mode. Answer in the fewest words possible. "
        "Bullet points, no preamble, no filler. " + _BASE),
}

MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
]

# ---- limits (tunable via env vars) --------------------------------------
MAX_REPLY_TOKENS = int(os.getenv("MAX_REPLY_TOKENS", "800"))
MAX_HISTORY_MESSAGES = 24        # only the most recent turns are sent on
MAX_MESSAGE_CHARS = 6000         # per message, longer is truncated
ALLOW_SEARCH = os.getenv("ALLOW_SEARCH", "true").lower() != "false"
RATE_CHAT = os.getenv("RATE_CHAT", "15 per minute;250 per day")
RATE_VOICE = os.getenv("RATE_VOICE", "10 per minute;120 per day")

load_dotenv()

if not os.getenv("GROQ_API_KEY"):
    raise SystemExit(
        "No API key found. Make a free key at https://console.groq.com/keys "
        "and put it in the .env file (GROQ_API_KEY=...)."
    )

APP_PASSWORD = os.getenv("APP_PASSWORD", "").strip()

client = Groq()
app = Flask(__name__)
# Trust one layer of reverse proxy (Render / Fly / etc.) so per-visitor
# rate limiting sees the real client IP, not the proxy's.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["400 per day"],
    storage_uri="memory://",
)


@app.before_request
def _password_gate():
    """If APP_PASSWORD is set, require it (browser shows a login box once)."""
    if not APP_PASSWORD or request.path == "/healthz":
        return
    auth = request.authorization
    if not auth or (auth.password or "") != APP_PASSWORD:
        return Response(
            "3RROR is password protected.", 401,
            {"WWW-Authenticate": 'Basic realm="3RROR"'},
        )


@app.errorhandler(429)
def _too_many(_e):
    return Response("Easy — you're sending requests too fast. Wait a minute.",
                    429, mimetype="text/plain")


def web_search(query, k=6):
    """Return a few live web results: [{title, url, snippet}]. Never raises."""
    query = (query or "").strip()
    if not query or not ALLOW_SEARCH:
        return []
    try:
        from ddgs import DDGS
        with DDGS() as ddg:
            hits = ddg.text(query, max_results=k)
        return [
            {"title": h.get("title", ""), "url": h.get("href", ""),
             "snippet": (h.get("body", "") or "")[:600]}
            for h in hits
        ]
    except Exception:
        return []


def clean_messages(raw):
    """Keep only recent, well-formed user/assistant turns and cap their size."""
    out = []
    for m in raw[-MAX_HISTORY_MESSAGES:]:
        role = m.get("role")
        content = m.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            out.append({"role": role, "content": content[:MAX_MESSAGE_CHARS]})
    while out and out[0]["role"] == "assistant":
        out.pop(0)
    return out


@app.get("/")
def index():
    return send_from_directory(".", "index.html")


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/config")
def config():
    return jsonify({
        "models": MODELS,
        "default": MODELS[0],
        "personas": [{"id": pid, "label": label} for pid, (label, _) in PERSONAS.items()],
        "search": ALLOW_SEARCH,
    })


@app.post("/transcribe")
@limiter.limit(RATE_VOICE)
def transcribe():
    """Turn a recorded voice clip into text using Groq's free Whisper model."""
    clip = request.files.get("audio")
    if clip is None:
        return jsonify({"error": "no audio uploaded"}), 400
    blob = clip.read(8 * 1024 * 1024)          # cap at 8 MB
    try:
        result = client.audio.transcriptions.create(
            model="whisper-large-v3-turbo",
            file=(clip.filename or "clip.webm", blob),
        )
        return jsonify({"text": (result.text or "").strip()})
    except AuthenticationError:
        return jsonify({"error": "API key looks invalid"}), 401
    except RateLimitError:
        return jsonify({"error": "the shared key is busy, try again in a minute"}), 429
    except APIStatusError as e:
        return jsonify({"error": f"API error {e.status_code}"}), 502
    except APIConnectionError:
        return jsonify({"error": "could not reach the internet"}), 502


@app.post("/chat")
@limiter.limit(RATE_CHAT)
def chat():
    """Stream a reply. Optional: `persona` id and `search` (live web lookup)."""
    data = request.get_json(force=True, silent=True) or {}
    user_messages = clean_messages(data.get("messages", []))
    if not user_messages:
        return Response("[no message]", mimetype="text/plain")
    model = data.get("model") if data.get("model") in MODELS else MODELS[0]
    persona = data.get("persona") if data.get("persona") in PERSONAS else "assistant"
    do_search = bool(data.get("search")) and ALLOW_SEARCH

    system = PERSONAS[persona][1]
    sources = []

    if do_search:
        query = next((m["content"] for m in reversed(user_messages)
                      if m["role"] == "user"), "")
        sources = web_search(query)
        if sources:
            block = "\n\n".join(
                f"[{i}] {s['title']}\n{s['url']}\n{s['snippet']}"
                for i, s in enumerate(sources, 1)
            )
            system += (
                "\n\nLive web search results for the user's latest question are "
                "below. Base your answer on them and cite facts inline as [n] "
                "matching the numbered list. If they do not answer the question, "
                "say so plainly.\n\n" + block
            )
        else:
            system += ("\n\n(Live web search was requested but returned nothing; "
                       "answer from your own knowledge and note that.)")

    messages = [{"role": "system", "content": system}] + user_messages

    def generate():
        try:
            stream = client.chat.completions.create(
                model=model, messages=messages, stream=True,
                max_tokens=MAX_REPLY_TOKENS,
            )
            for chunk in stream:
                yield chunk.choices[0].delta.content or ""
        except AuthenticationError:
            yield "\n\n[Error: the API key looks invalid.]"
        except RateLimitError:
            yield "\n\n[The shared key is busy right now. Try again in a minute.]"
        except APIStatusError as e:
            yield f"\n\n[API error {e.status_code}: {getattr(e, 'message', e)}]"
        except APIConnectionError:
            yield "\n\n[Error: could not reach the internet.]"

    resp = Response(generate(), mimetype="text/plain")
    if sources:
        resp.headers["X-Sources"] = json.dumps(
            [{"t": s["title"][:120], "u": s["url"]} for s in sources]
        )[:7000]
    return resp


if __name__ == "__main__":
    # Local dev only. In production, gunicorn runs `web:app` (see README).
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=True)
