# my-ai (3rror)

A tiny chatbot — command line **and** web interface. It remembers the
conversation and streams replies as they are generated.

**Cost: $0.** It runs on [Groq](https://console.groq.com), which gives you a
free API tier with no credit card. The model is an open model (GPT-OSS) hosted by Groq.

## One-time setup

Run these in **PowerShell**, inside this folder
(`C:\Users\Administrator\Claude\my-ai`).

### 1. Get a free key

1. Go to https://console.groq.com/keys (sign in with Google — no card needed).
2. Click **Create API Key**, copy it (starts with `gsk_...`).

### 2. Add the key

Open `.env` in this folder and paste it after the `=`:

```
GROQ_API_KEY=gsk_your_key_here
```

Save. Never share this file.

## Run it

**Web interface** (open http://localhost:5000 after) — a futuristic HUD:

```bash
.\.venv\Scripts\python.exe web.py
```

What it can do:

| Control | What it does |
|---|---|
| **Persona** dropdown | Assistant · Engineer · Tutor · Brainstorm · Devil's Advocate · Briefing |
| **🌐 web** | Live web search (DuckDuckGo) — answers cite numbered sources |
| **🔊 speak** | Reads replies aloud, then pick a voice under **Settings** |
| **🎙 mic** | Speak instead of type — transcribed by Groq's free Whisper |
| **🔊 + 🎙 together** | Hands-free: it listens, answers, speaks, listens again. Press Esc to stop. |
| **Settings** | Model, voice, appearance (Nebula / Dawn), interface sounds |

The first time you use the mic, allow microphone permission. Voice needs
Chrome, Edge, or Firefox.

**For the best-sounding voice:** open the app in **Microsoft Edge** — it has
free "Natural" AI voices (Aria, Guy, …) that sound modern. Chrome only has the
older robotic system voices unless you install more from Windows Settings →
Time & language → Speech.

**Command line:**

```bash
.\.venv\Scripts\python.exe chat.py
```

## Make it your own

Edit the settings near the top of `web.py`:

- `PERSONAS` — the personality dropdown. Add your own, or edit the wording.
- `MODELS` — `openai/gpt-oss-120b` (smart) or `openai/gpt-oss-20b` (fast).
  See models your key can use: https://console.groq.com/docs/models

(`chat.py` is the simple terminal version and still uses a single `SYSTEM_PROMPT`.)

## Put it online (free) so other people can use it

Hosted on **[Render](https://render.com)** — free, HTTPS URL, no credit card.

**1. Put the code on GitHub**

```bash
git init
git add .
git commit -m "3RROR"
```

Then make an empty repo at https://github.com/new and follow its
"push an existing repository" lines. (`.env` is git-ignored — your key is **not**
uploaded.)

**2. Deploy on Render**

1. Sign up at https://render.com with your GitHub account.
2. **New +** → **Blueprint** → pick your repo. It reads `render.yaml`.
3. When asked, paste your `GROQ_API_KEY` value. Optionally set `APP_PASSWORD`
   to a word visitors must enter once.
4. **Apply**. In ~2 minutes you get `https://3rror.onrender.com` to share.

> Free Render apps sleep after 15 min idle and take ~50s to wake on the next
> visit. To keep it warm, add a free monitor at
> [uptimerobot.com](https://uptimerobot.com) pinging `https://your-url/healthz`
> every 5 minutes.

**Good to know about sharing**

- Everyone who visits uses **your one Groq key** and its free rate limits. A busy
  moment can slow everyone down; sustained heavy use is billed to you if you ever
  add card details to Groq.
- Built-in protection: each visitor is limited to ~15 messages/minute, replies
  are capped, only recent history is sent, and `APP_PASSWORD` gates the whole app.
- Tune it with env vars in Render: `RATE_CHAT`, `RATE_VOICE`, `MAX_REPLY_TOKENS`,
  `ALLOW_SEARCH=false`.

**Just a few friends?** Skip hosting — run `web.py` locally and expose it with
[`cloudflared tunnel --url http://localhost:5000`](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/)
(free, gives a temporary public URL, only works while your PC is on).

## Files

| File | What it is |
|------|-----------|
| `web.py` | The web server (Flask). Serves the page + talks to Groq. |
| `index.html` | The chat web page (HTML + JavaScript). |
| `chat.py` | The command-line version. |
| `.env` | Your secret key. Git-ignored, never uploaded. |
| `requirements.txt` | Python libraries. |
| `render.yaml` / `Procfile` | Deploy config for Render / other hosts. |

Reinstall libraries any time with:

```bash
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```
