from typing import List, Optional
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Listing, Wishlist
from app.auth import get_current_user, require_login
from app.services.storage_utils import parse_extra_attributes, save_upload_image
from app.services.listing_service import create_listing_record

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# Renders sell form with dynamic categories dropdown
@router.get("/sell", response_class=HTMLResponse)
def get_sell_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_login)
):
    categories_raw = db.query(Listing.category).distinct().order_by(Listing.category).all()
    categories = [c[0] for c in categories_raw if c[0]]
    if not categories:
        categories = [
            "BABY_PRODUCTS", "BEAUTY_HEALTH", "CLOTHING_ACCESSORIES_JEWELLERY",
            "ELECTRONICS", "GROCERY", "HOBBY_ARTS_STATIONERY",
            "HOME_KITCHEN_TOOLS", "PET_SUPPLIES", "SPORTS_OUTDOOR",
            "car", "furniture"
        ]

    return templates.TemplateResponse(
        request=request,
        name="sell.html",
        context={"current_user": current_user, "categories": categories}
    )


# Single form handling function to be easily swapped for an AI-powered flow later
@router.post("/sell")
def handle_sell_form(
    request: Request,
    title: str = Form(...),
    category: str = Form(...),
    price: float = Form(...),
    condition: str = Form(...),
    description: str = Form(""),
    extra_details: str = Form(""),
    images: List[UploadFile] = File([]),
    db: Session = Depends(get_db),
    current_user=Depends(require_login)
):
    saved_urls = []
    for upload in images[:3]:
        if upload and upload.filename:
            url = save_upload_image(upload)
            if url:
                saved_urls.append(url)

    attributes = parse_extra_attributes(extra_details)

    listing = create_listing_record(
        db=db,
        user_id=current_user.id,
        title=title.strip(),
        category=category.strip(),
        price=price,
        condition=condition.strip(),
        description=description.strip(),
        image_urls=saved_urls,
        attributes=attributes
    )

    return RedirectResponse(url=f"/listing/{listing.id}", status_code=303)


# Displays user's own created listings
@router.get("/my-listings", response_class=HTMLResponse)
def get_my_listings(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_login)
):
    listings = db.query(Listing).filter(Listing.user_id == current_user.id).order_by(Listing.created_at.desc()).all()
    wishlist_ids = {str(item.id) for item in listings}

    return templates.TemplateResponse(
        request=request,
        name="my_listings.html",
        context={
            "current_user": current_user,
            "listings": listings,
            "wishlist_ids": wishlist_ids
        }
    )
