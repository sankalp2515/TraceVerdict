"""Generate missing local credentials without displaying or replacing existing secrets."""
from pathlib import Path
import secrets

from dotenv import dotenv_values, set_key

ROOT = Path(__file__).resolve().parents[1]


def main():
    target = ROOT / ".env"
    if not target.exists():
        target.write_text((ROOT / ".env.example").read_text(encoding="utf-8"), encoding="utf-8")
    values = dotenv_values(target)
    generated = []
    for name in ["TRACEVERDICT_ADMIN_KEY", "TRACEVERDICT_PROJECT_KEY", *[
        f"TV_{group}_{suffix}" for group in ("EVENTS", "CONFIGURATION", "REFERENCE")
        for suffix in ("PASSWORD", "READER_PASSWORD")]]:
        if not values.get(name):
            values[name] = secrets.token_hex(32)
            set_key(target, name, values[name])
            generated.append(name)
    defaults = {"TRACEVERDICT_DB_URL": f"postgresql://tv_owner:{values['TV_EVENTS_PASSWORD']}@127.0.0.1:54331/events",
                "TRACEVERDICT_COOKIE_SECURE": "false"}
    for name, value in defaults.items():
        if not values.get(name):
            set_key(target, name, value)
    print("Private local configuration ready. Generated variable names: " + ", ".join(generated))
    print("Set sponsor endpoints and credentials privately in .env; use HTTPS and secure cookies for deployment.")


if __name__ == "__main__":
    main()
