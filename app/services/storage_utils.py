import os
import uuid
import shutil
from pathlib import Path
from typing import List, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "app" / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

USE_SUPABASE = os.getenv("USE_SUPABASE_STORAGE", "false").strip().lower() in ("true", "1", "yes")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "listing-images")

# Parses user-entered extra details multiline text into key-value tuples
def parse_extra_attributes(raw_text: str) -> List[Tuple[str, str]]:
    attributes = []
    if not raw_text:
        return attributes
    for line in raw_text.strip().splitlines():
        if ":" in line:
            parts = line.split(":", 1)
            k, v = parts[0].strip(), parts[1].strip()
            if k and v:
                attributes.append((k, v))
    return attributes


# Saves uploaded file to Supabase Storage or falls back to app/static/uploads/
def save_upload_image(upload_file) -> str:
    if not upload_file or not upload_file.filename:
        return ""
    ext = Path(upload_file.filename).suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"

    if USE_SUPABASE and SUPABASE_URL and SUPABASE_KEY:
        try:
            from supabase import create_client
            client = create_client(SUPABASE_URL, SUPABASE_KEY)
            content = upload_file.file.read()
            client.storage.from_(SUPABASE_BUCKET).upload(
                path=filename,
                file=content,
                file_options={"content-type": upload_file.content_type or "image/jpeg"}
            )
            return client.storage.from_(SUPABASE_BUCKET).get_public_url(filename)
        except Exception:
            pass

    # Local fallback
    dest = UPLOAD_DIR / filename
    with open(dest, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return f"/static/uploads/{filename}"
