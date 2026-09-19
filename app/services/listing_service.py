import uuid
from decimal import Decimal
from typing import List, Tuple
from sqlalchemy.orm import Session
from app.models import Listing, ListingImage, ListingAttribute, ListingEmbedding


# Encapsulates clean database persistence logic for new listings
def create_listing_record(
    db: Session,
    user_id,
    title: str,
    category: str,
    price: float,
    condition: str,
    description: str,
    image_urls: List[str],
    attributes: List[Tuple[str, str]]
) -> Listing:
    listing = Listing(
        user_id=user_id,
        title=title,
        category=category,
        price=Decimal(str(price)),
        condition=condition,
        description=description,
        status="active"
    )
    db.add(listing)
    db.flush()

    for idx, url in enumerate(image_urls):
        if url:
            img = ListingImage(
                listing_id=listing.id,
                image_url=url,
                is_primary=(idx == 0)
            )
            db.add(img)

    for k, v in attributes:
        attr = ListingAttribute(
            listing_id=listing.id,
            key=k,
            value=v
        )
        db.add(attr)

    embedding = ListingEmbedding(
        listing_id=listing.id,
        embedding_vector=None
    )
    db.add(embedding)

    db.commit()
    db.refresh(listing)
    return listing
