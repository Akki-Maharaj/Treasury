# Embeds every listing whose vector is missing (no row, SQL NULL, or JSON null).
import sys, os
# Lets the script import from app/ when run from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy.orm import selectinload
from sentence_transformers import SentenceTransformer
from app.db import SessionLocal
from app.models import Listing, ListingEmbedding


def build_text(l):
    # Title + category + attribute values, so similar items land close together
    attrs = " ".join(a.value for a in l.attributes)
    return f"{l.title} {l.category} {attrs}".strip()


def main(force=False):
    db = SessionLocal()
    # selectinload fetches all attributes in one query instead of one per listing
    listings = db.query(Listing).options(selectinload(Listing.attributes)).all()
    rows = {e.listing_id: e for e in db.query(ListingEmbedding).all()}
    # "not vector" is True for None, so it also catches a JSON null
    todo = [l for l in listings if force or not rows.get(l.id) or not rows[l.id].embedding_vector]
    print(f"{len(listings)} listings, {len(todo)} need embeddings")
    if not todo:
        return

    model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    for i in range(0, len(todo), 64):
        batch = todo[i:i + 64]
        vecs = model.encode([build_text(l) for l in batch], normalize_embeddings=True)
        for l, v in zip(batch, vecs):
            row = rows.get(l.id)
            if row is None:
                row = ListingEmbedding(listing_id=l.id)
                db.add(row)
            row.embedding_vector = [float(x) for x in v]
        db.commit()
        print(f"embedded {min(i + 64, len(todo))}/{len(todo)}")
    db.close()


if __name__ == "__main__":
    main(force="--force" in sys.argv)