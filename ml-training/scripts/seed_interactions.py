import sys
import random
import argparse
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.db import SessionLocal
from app.models import User, Listing, Interaction, Wishlist
from app.auth import hash_password

FIRST_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan", "Sam", "Chris", "Pat", "Riley", "Casey", "Avery",
    "Jamie", "Cameron", "Dakota", "Reese", "Quinn", "Skyler", "Jesse", "Kendall", "Peyton", "Logan"
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"
]

def get_or_create_buyers(db, num_buyers=60):
    hashed_pwd = hash_password("demo1234")
    buyers = []
    created_count = 0

    for i in range(1, num_buyers + 1):
        email = f"buyer{i}@demo.com"
        user = db.query(User).filter(User.email == email).first()
        if not user:
            name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            phone = f"{random.randint(10000000, 99999999)}"
            user = User(
                name=name,
                email=email,
                password_hash=hashed_pwd,
                phone=phone
            )
            db.add(user)
            db.flush()
            created_count += 1
        buyers.append(user)

    db.commit()
    return buyers, created_count

def reset_fake_buyers_data(db):
    fake_users = db.query(User).filter(User.email.like("buyer%@demo.com")).all()
    user_ids = [u.id for u in fake_users]
    if not user_ids:
        print("No fake buyers found to reset.")
        return

    # Delete interactions and wishlist rows belonging to fake buyers
    i_count = db.query(Interaction).filter(Interaction.user_id.in_(user_ids)).delete(synchronize_session=False)
    w_count = db.query(Wishlist).filter(Wishlist.user_id.in_(user_ids)).delete(synchronize_session=False)
    db.commit()
    print(f"Reset completed: deleted {i_count} interactions and {w_count} wishlist entries.")

def seed_interactions(reset=False):
    db = SessionLocal()
    try:
        if reset:
            reset_fake_buyers_data(db)

        buyers, created_count = get_or_create_buyers(db, 60)
        print(f"Buyers ready (created: {created_count}, total: {len(buyers)}).")

        # Fetch active listings grouped by category
        listings = db.query(Listing).filter(Listing.status == "active").all()
        if not listings:
            print("No active listings found in database.")
            return

        categories = list({l.category for l in listings if l.category})
        if not categories:
            print("No categories found.")
            return

        total_interactions_added = 0
        total_wishlists_added = 0

        # Price bands definitions: low, mid, high, luxury
        price_bands = [
            (0, 50),
            (30, 150),
            (100, 500),
            (300, 2000),
            (1000, 100000)
        ]

        for idx, buyer in enumerate(buyers):
            # Check if user already has interactions
            existing_count = db.query(Interaction).filter(Interaction.user_id == buyer.id).count()
            if existing_count > 0 and not reset:
                continue

            # Deterministic/semi-random profile per buyer
            random.seed(buyer.id * 37)
            # Pick 1-2 preferred categories
            num_pref = 1 if len(categories) == 1 else random.choice([1, 2])
            pref_cats = set(random.sample(categories, min(num_pref, len(categories))))
            p_min, p_max = random.choice(price_bands)

            # Preferred pool vs Noise pool
            pref_pool = [
                l for l in listings
                if l.category in pref_cats and p_min <= float(l.price) <= p_max
            ]
            # Fallback if preferred pool is too small: just category match
            if len(pref_pool) < 5:
                pref_pool = [l for l in listings if l.category in pref_cats]
            if not pref_pool:
                pref_pool = listings

            num_interactions = random.randint(20, 40)
            seen_for_user = set()

            for _ in range(num_interactions):
                # 75% preferred, 25% noise
                if random.random() < 0.75 and pref_pool:
                    target_listing = random.choice(pref_pool)
                else:
                    target_listing = random.choice(listings)

                # ~80% views and ~20% wishlist
                is_wishlist = random.random() < 0.20
                itype = "wishlist" if is_wishlist else "view"

                interaction = Interaction(
                    user_id=buyer.id,
                    listing_id=target_listing.id,
                    type=itype
                )
                db.add(interaction)
                total_interactions_added += 1

                if is_wishlist and target_listing.id not in seen_for_user:
                    wish = Wishlist(
                        user_id=buyer.id,
                        listing_id=target_listing.id
                    )
                    db.add(wish)
                    seen_for_user.add(target_listing.id)
                    total_wishlists_added += 1

        db.commit()
        print(f"Seeding complete! Added {total_interactions_added} interactions and {total_wishlists_added} wishlist rows.")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Delete fake buyers' interactions and wishlist items")
    args = parser.parse_args()
    seed_interactions(reset=args.reset)
