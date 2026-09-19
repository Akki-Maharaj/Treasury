import uuid
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Wishlist, Listing, Interaction
from app.auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# Adds or removes a listing from the user's wishlist via AJAX and records interaction
@router.post("/wishlist/toggle/{listing_id}")
def toggle_wishlist(
    listing_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if not current_user:
        return JSONResponse({"error": "unauthorized", "redirect": "/login"}, status_code=401)

    try:
        parsed_id = int(listing_id)
    except (ValueError, TypeError):
        try:
            parsed_id = uuid.UUID(listing_id)
        except (ValueError, TypeError):
            return JSONResponse({"error": "invalid listing id"}, status_code=400)

    existing = db.query(Wishlist).filter(
        Wishlist.user_id == current_user.id,
        Wishlist.listing_id == parsed_id
    ).first()

    if existing:
        db.delete(existing)
        db.commit()
        return JSONResponse({"saved": False})
    else:
        wish = Wishlist(user_id=current_user.id, listing_id=parsed_id)
        db.add(wish)
        # Log interaction for user taste profiling
        interaction = Interaction(
            user_id=current_user.id,
            listing_id=parsed_id,
            type="wishlist"
        )
        db.add(interaction)
        db.commit()
        return JSONResponse({"saved": True})


# Displays user's saved wishlist listings in the standard card grid
@router.get("/wishlist", response_class=HTMLResponse)
def get_wishlist(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if not current_user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login?next=/wishlist", status_code=303)

    items = db.query(Listing).join(Wishlist, Wishlist.listing_id == Listing.id)\
        .filter(Wishlist.user_id == current_user.id)\
        .order_by(Wishlist.created_at.desc()).all()

    wishlist_ids = {str(item.id) for item in items}

    return templates.TemplateResponse(
        request=request,
        name="wishlist.html",
        context={
            "current_user": current_user,
            "listings": items,
            "wishlist_ids": wishlist_ids
        }
    )
