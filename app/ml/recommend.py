import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db import SessionLocal
from app.models import Listing, ListingEmbedding, Interaction

# Global in-memory cache of listing embeddings
_EMBEDDINGS_MATRIX = None
_LISTING_IDS = []
_ID_TO_ROW = {}

def reload_embeddings(db: Session = None):
    """Loads all listing embeddings into one numpy matrix plus an id->row map."""
    global _EMBEDDINGS_MATRIX, _LISTING_IDS, _ID_TO_ROW

    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        # Load only listings that have non-null embedding vectors
        records = (
            db.query(ListingEmbedding.listing_id, ListingEmbedding.embedding_vector)
            .filter(ListingEmbedding.embedding_vector.isnot(None))
            .all()
        )

        listing_ids = []
        vectors = []
        id_to_row = {}

        for idx, (lid, vec) in enumerate(records):
            if vec and len(vec) > 0:
                listing_ids.append(lid)
                vectors.append(vec)
                id_to_row[lid] = len(vectors) - 1

        if vectors:
            matrix = np.array(vectors, dtype=np.float32)
            # Ensure row-wise normalization for exact cosine dot products
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            matrix = matrix / norms
            _EMBEDDINGS_MATRIX = matrix
        else:
            _EMBEDDINGS_MATRIX = np.empty((0, 384), dtype=np.float32)

        _LISTING_IDS = listing_ids
        _ID_TO_ROW = id_to_row
    finally:
        if close_db:
            db.close()

def _get_active_listing_ids(db: Session) -> set:
    """Helper to get set of currently active listing IDs."""
    rows = db.query(Listing.id).filter(Listing.status == "active").all()
    return {r[0] for r in rows}

def _get_cold_start_listings(db: Session, k: int = 12) -> list[int]:
    """Returns top-k most-interacted active listings for cold start."""
    active_ids = _get_active_listing_ids(db)
    # Count interactions per listing
    popular_counts = (
        db.query(Interaction.listing_id, func.count(Interaction.id).label("cnt"))
        .group_by(Interaction.listing_id)
        .order_by(func.count(Interaction.id).desc())
        .all()
    )

    popular_ids = [lid for lid, _ in popular_counts if lid in active_ids]

    # Fallback to recent active listings if popular count is smaller than k
    if len(popular_ids) < k:
        recent = (
            db.query(Listing.id)
            .filter(Listing.status == "active")
            .order_by(Listing.created_at.desc())
            .limit(k * 2)
            .all()
        )
        for (lid,) in recent:
            if lid not in popular_ids:
                popular_ids.append(lid)
            if len(popular_ids) >= k:
                break

    return popular_ids[:k]

def recommend_for_user(user_id: int | None, db: Session, k: int = 12) -> list[int]:
    """Recommends top-k listing ids using weighted interaction embeddings."""
    if _EMBEDDINGS_MATRIX is None or len(_LISTING_IDS) == 0:
        reload_embeddings(db)

    if not user_id:
        return _get_cold_start_listings(db, k)

    # Fetch user interactions
    interactions = db.query(Interaction).filter(Interaction.user_id == user_id).all()
    if not interactions:
        return _get_cold_start_listings(db, k)

    # Exclude listings user already interacted with or owns
    interacted_ids = {i.listing_id for i in interactions}
    owned_ids = {r[0] for r in db.query(Listing.id).filter(Listing.user_id == user_id).all()}
    excluded_ids = interacted_ids | owned_ids

    # Weighted sum: wishlist = 3, view = 1
    user_vec = np.zeros(_EMBEDDINGS_MATRIX.shape[1], dtype=np.float32)
    weight_sum = 0.0

    for inter in interactions:
        row_idx = _ID_TO_ROW.get(inter.listing_id)
        if row_idx is not None:
            w = 3.0 if inter.type == "wishlist" else 1.0
            user_vec += _EMBEDDINGS_MATRIX[row_idx] * w
            weight_sum += w

    if weight_sum == 0.0:
        return _get_cold_start_listings(db, k)

    norm = np.linalg.norm(user_vec)
    if norm > 0:
        user_vec = user_vec / norm

    # Cosine similarity by dot product
    scores = np.dot(_EMBEDDINGS_MATRIX, user_vec)
    # Sort descending
    ranked_indices = np.argsort(-scores)

    active_ids = _get_active_listing_ids(db)
    recommendations = []
    for idx in ranked_indices:
        lid = _LISTING_IDS[idx]
        if lid not in excluded_ids and lid in active_ids:
            recommendations.append(lid)
            if len(recommendations) >= k:
                break

    # If not enough, fill with cold-start items
    if len(recommendations) < k:
        for cid in _get_cold_start_listings(db, k):
            if cid not in excluded_ids and cid not in recommendations:
                recommendations.append(cid)
            if len(recommendations) >= k:
                break

    return recommendations

def similar_listings(listing_id: int, db: Session = None, k: int = 6) -> list[int]:
    """Returns top-k listing ids similar to listing_id by cosine similarity."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        if _EMBEDDINGS_MATRIX is None or len(_LISTING_IDS) == 0:
            reload_embeddings(db)

        target_row = _ID_TO_ROW.get(listing_id)
        if target_row is None or _EMBEDDINGS_MATRIX is None or len(_EMBEDDINGS_MATRIX) == 0:
            return []

        target_vec = _EMBEDDINGS_MATRIX[target_row]
        scores = np.dot(_EMBEDDINGS_MATRIX, target_vec)
        ranked_indices = np.argsort(-scores)

        active_ids = _get_active_listing_ids(db)
        similar = []
        for idx in ranked_indices:
            lid = _LISTING_IDS[idx]
            if lid != listing_id and lid in active_ids:
                similar.append(lid)
                if len(similar) >= k:
                    break

        return similar
    finally:
        if close_db:
            db.close()

# Initial load into memory at import time
try:
    reload_embeddings()
except Exception:
    # Fail-safe if DB is initializing or empty
    pass
