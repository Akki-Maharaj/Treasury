import uuid
import math
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db import get_db
from app.models import Listing, ListingImage, ListingAttribute, Wishlist, Interaction
from app.auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# Renders home page with filters, search, pagination, wishlist markers, and recommendation placeholder
@router.get("/", response_class=HTMLResponse)
def get_home(
    request: Request,
    page: int = 1,
    category: str = "",
    q: str = "",
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    page = max(1, page)
    per_page = 24

    query = db.query(Listing).filter(Listing.status == "active")
    if category.strip():
        query = query.filter(Listing.category == category.strip())
    if q.strip():
        search_pattern = f"%{q.strip()}%"
        query = query.filter(Listing.title.ilike(search_pattern))

    total_listings = query.count()
    total_pages = max(1, math.ceil(total_listings / per_page))
    listings = query.order_by(Listing.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    # Pre-fetch user's wishlist IDs for instant heart rendering
    wishlist_ids = set()
    if current_user:
        user_wishes = db.query(Wishlist.listing_id).filter(Wishlist.user_id == current_user.id).all()
        wishlist_ids = {str(item[0]) for item in user_wishes}

    # Distinct categories for the filter bar
    categories_raw = db.query(Listing.category).distinct().order_by(Listing.category).all()
    categories = [c[0] for c in categories_raw if c[0]]

    # Personalized recommendations or cold start
    from app.ml.recommend import recommend_for_user
    rec_ids = recommend_for_user(current_user.id if current_user else None, db, k=12)
    recommended_listings = []
    rec_subtitle = "Popular right now"
    if rec_ids:
        id_order = {lid: idx for idx, lid in enumerate(rec_ids)}
        rec_objs = db.query(Listing).filter(Listing.id.in_(rec_ids)).all()
        recommended_listings = sorted(rec_objs, key=lambda l: id_order.get(l.id, 999))
        if current_user:
            has_history = db.query(Interaction.id).filter(Interaction.user_id == current_user.id).first()
            if has_history:
                rec_subtitle = "Picked for you"

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "current_user": current_user,
            "listings": listings,
            "recommended_listings": recommended_listings,
            "rec_subtitle": rec_subtitle,
            "wishlist_ids": wishlist_ids,
            "categories": categories,
            "selected_category": category,
            "search_query": q,
            "page": page,
            "total_pages": total_pages,
            "total_listings": total_listings
        }
    )


# Renders single listing detail view, records user view interaction, and lists key attributes
@router.get("/listing/{id}", response_class=HTMLResponse)
def get_listing_detail(
    request: Request,
    id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        listing = db.query(Listing).filter(Listing.id == int(id)).first()
    except (ValueError, TypeError):
        try:
            listing = db.query(Listing).filter(Listing.id == uuid.UUID(id)).first()
        except (ValueError, TypeError):
            raise HTTPException(status_code=404, detail="Invalid listing ID")

    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Track user interaction for recommendation telemetry
    if current_user:
        interaction = Interaction(
            user_id=current_user.id,
            listing_id=listing.id,
            type="view"
        )
        db.add(interaction)
        db.commit()

    is_saved = False
    wishlist_ids = set()
    if current_user:
        exists = db.query(Wishlist).filter(
            Wishlist.user_id == current_user.id,
            Wishlist.listing_id == listing.id
        ).first()
        is_saved = bool(exists)
        user_wishes = db.query(Wishlist.listing_id).filter(Wishlist.user_id == current_user.id).all()
        wishlist_ids = {str(item[0]) for item in user_wishes}

    # Fetch similar listings using embeddings
    from app.ml.recommend import similar_listings
    sim_ids = similar_listings(listing.id, db=db, k=6)
    similar_items = []
    if sim_ids:
        sim_order = {lid: idx for idx, lid in enumerate(sim_ids)}
        sim_objs = db.query(Listing).filter(Listing.id.in_(sim_ids)).all()
        similar_items = sorted(sim_objs, key=lambda l: sim_order.get(l.id, 999))

    return templates.TemplateResponse(
        request=request,
        name="listing.html",
        context={
            "current_user": current_user,
            "listing": listing,
            "is_saved": is_saved,
            "similar_items": similar_items,
            "wishlist_ids": wishlist_ids
        }
    )
