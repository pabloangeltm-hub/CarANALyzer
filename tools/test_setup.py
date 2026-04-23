"""
Validates the environment: checks required vars are set and tests live connections.
Run this after any change to .env or after first setup.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

errors = []
warnings = []

# --- Anthropic ---
anthropic_key = os.getenv("ANTHROPIC_API_KEY")
if not anthropic_key:
    errors.append("ANTHROPIC_API_KEY is not set")
else:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=anthropic_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": "ping"}],
        )
        print("[OK] Anthropic API connected")
    except Exception as e:
        errors.append(f"Anthropic API error: {e}")

# --- Google OAuth ---
if not os.path.exists("credentials.json"):
    warnings.append("credentials.json not found — Google tools won't work until you add it")
else:
    print("[OK] credentials.json found")

if not os.getenv("GOOGLE_SHEET_ID"):
    warnings.append("GOOGLE_SHEET_ID not set in .env")

if not os.getenv("GOOGLE_SLIDES_ID"):
    warnings.append("GOOGLE_SLIDES_ID not set in .env")

# --- Report ---
print()
for w in warnings:
    print(f"[WARN] {w}")
for e in errors:
    print(f"[ERROR] {e}")

if errors:
    print("\nSetup incomplete. Fix the errors above before running tools.")
    sys.exit(1)
elif warnings:
    print("\nSetup partial. Anthropic tools are ready; Google tools need configuration.")
else:
    print("\nAll systems go.")
