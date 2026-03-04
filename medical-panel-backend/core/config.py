"""Configuration helpers for the backend.

We explicitly load the .env file from the backend directory so that
the value is discovered even if the server is started from a different
working directory (e.g. from the workspace root).  This was causing
users to think they had provided a valid Gemini key when in fact the
environment variable was never being read, and the system silently
fell back to a mock model.

Note: dotenv.load_dotenv() without arguments only searches the current
working directory.  By computing the path relative to this module we
make the behaviour deterministic.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# locate the .env file in the backend folder regardless of cwd
base_dir = Path(__file__).parent.parent
env_path = base_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # fall back to default behaviour; load_dotenv will try cwd
    load_dotenv()

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    print('Warning: GOOGLE_API_KEY not found in environment.  The server will run in mock mode.')
else:
    # redacted log to avoid leaking secrets
    print(f'GOOGLE_API_KEY detected: {GOOGLE_API_KEY[:4]}...{GOOGLE_API_KEY[-4:]} (redacted)')

# Allow overriding the LLM model name via environment for flexibility.
# Defaults to a general-purpose Gemini model; the previous hardcoded
# "gemini-1.5-flash" is no longer available in some API versions, which
# resulted in NOT_FOUND errors.  Set GOOGLE_MODEL in .env if you need a
# different model (e.g. gemini-1.5, gemini-2.1, etc.).
GOOGLE_MODEL = os.getenv('GOOGLE_MODEL', 'gemini-2.5-flash')
print(f'Using Google model: {GOOGLE_MODEL}')
