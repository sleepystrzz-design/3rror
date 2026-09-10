r"""
my-ai — a simple command-line chatbot.

Uses Groq (https://console.groq.com) which has a FREE API tier — no credit
card, no charges. The model is Llama, an open model hosted by Groq.

Run it with:   .\.venv\Scripts\python.exe chat.py
Quit any time by typing:   quit   (or pressing Ctrl+C)

How it works:
  1. We load your free Groq API key from the .env file.
  2. We keep a list called `history` with everything said so far.
  3. Each time you type something, we send the whole history to the model
     and stream its reply back one piece at a time.
"""

import os
import sys

from dotenv import load_dotenv
from groq import Groq, AuthenticationError, RateLimitError, APIStatusError, APIConnectionError

# ---------------------------------------------------------------------------
# Settings you can safely change
# ---------------------------------------------------------------------------

# Which model to use (all free on Groq):
#   "openai/gpt-oss-120b" -> smartest (default)
#   "openai/gpt-oss-20b"  -> faster
#   "qwen/qwen3.8-27b"    -> another good option
# See models your key can use at https://console.groq.com/docs/models
MODEL = "openai/gpt-oss-120b"

# The "personality" of your AI. Rewrite this however you like.
SYSTEM_PROMPT = (
    "You are 3rror, a friendly and concise personal assistant. "
    "Explain things simply and warmly. When you are not sure, say so."
)

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

load_dotenv()  # reads the .env file and puts GROQ_API_KEY into the environment

if not os.getenv("GROQ_API_KEY"):
    print(
        "No API key found.\n"
        "1. Make a FREE key at https://console.groq.com/keys (no card needed)\n"
        "2. Open the file named .env and put it after GROQ_API_KEY="
    )
    sys.exit(1)

client = Groq()  # automatically picks up GROQ_API_KEY

# The running transcript. The first entry is the personality/system message.
history = [{"role": "system", "content": SYSTEM_PROMPT}]


def ask(user_message: str) -> str:
    """Send one message to the model and stream the reply to the screen."""
    history.append({"role": "user", "content": user_message})

    reply_parts = []
    print("\n3rror: ", end="", flush=True)

    try:
        stream = client.chat.completions.create(
            model=MODEL,
            messages=history,
            stream=True,
        )
        for chunk in stream:
            piece = chunk.choices[0].delta.content or ""
            print(piece, end="", flush=True)
            reply_parts.append(piece)
    except AuthenticationError:
        print("\n[Your API key seems to be invalid. Check the .env file.]")
        history.pop()
        return ""
    except RateLimitError:
        print("\n[Hit the free rate limit. Wait a minute and try again.]")
        history.pop()
        return ""
    except APIStatusError as e:
        print(f"\n[API error {e.status_code}: {getattr(e, 'message', e)}]")
        history.pop()
        return ""
    except APIConnectionError:
        print("\n[Could not reach the internet. Check your connection.]")
        history.pop()
        return ""

    print()  # newline after the streamed reply
    reply = "".join(reply_parts)
    history.append({"role": "assistant", "content": reply})
    return reply


def main() -> None:
    print("3rror is ready. Type a message, or 'quit' to leave.")
    while True:
        try:
            user_message = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            return

        if user_message.lower() in {"quit", "exit", "bye"}:
            print("Bye!")
            return

        if user_message:
            ask(user_message)


if __name__ == "__main__":
    main()
