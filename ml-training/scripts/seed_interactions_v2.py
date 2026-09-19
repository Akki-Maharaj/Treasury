# Fake buyers with category + price-band tastes, so the recommender has a real signal to learn.
import sys, random
from pathlib import Path
import bcrypt

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.db import SessionLocal
from app.models import User, Listing, Interaction, Wishlist

random.seed(7)


def main():
    db = SessionLocal()
    rows = db.query(Listing.id, Listing.category, Listing.price).filter(Listing.status == "active").all()
    by_cat = {}
    for i, c, p in rows:
        by_cat.setdefault(c, []).append((i, float(p)))
    for c in by_cat:
        by_cat[c].sort(key=lambda x: x[1])  # sorted by price so we can slice a price band
    all_ids = [r[0] for r in rows]

    # Buyers (password hash is NOT NULL in the DB, so hash once and reuse)
    pw = bcrypt.hashpw(b"demo1234", bcrypt.gensalt()).decode()
    for n in range(1, 61):
        email = f"buyer{n}@demo.com"
        if not db.query(User).filter_by(email=email).first():
            db.add(User(name=f"Buyer {n}", email=email, password_hash=pw,
                        phone=str(random.randint(10**7, 10**8 - 1))))
    db.commit()
    buyers = [i for (i,) in db.query(User.id).filter(User.email.like("buyer%@demo.com"))]

    if "--reset" in sys.argv:
        db.query(Interaction).filter(Interaction.user_id.in_(buyers)).delete(synchronize_session=False)
        db.query(Wishlist).filter(Wishlist.user_id.in_(buyers)).delete(synchronize_session=False)
        db.commit()
    elif db.query(Interaction).filter(Interaction.user_id.in_(buyers)).count() > 0:
        print("Buyers already have interactions. Use --reset to redo.")
        return

    total = 0
    for uid in buyers:
        prefs = random.sample(list(by_cat), 2)          # each buyer likes 2 categories
        lo_q = random.uniform(0, 0.5)                    # and a price band (half of the price range)
        pool = []
        for c in prefs:
            items = by_cat[c]
            a, b = int(len(items) * lo_q), int(len(items) * (lo_q + 0.5))
            pool += [i for i, _ in items[a:b]] or [i for i, _ in items]
        seen, wished = set(), set()
        for _ in range(random.randint(20, 40)):
            # 75% follows taste, 25% random noise
            lid = random.choice(pool) if random.random() < 0.75 else random.choice(all_ids)
            kind = "wishlist" if random.random() < 0.2 else "view"
            if (lid, kind) in seen:
                continue
            seen.add((lid, kind))
            db.add(Interaction(user_id=uid, listing_id=lid, type=kind))
            total += 1
            if kind == "wishlist" and lid not in wished:
                wished.add(lid)
                db.add(Wishlist(user_id=uid, listing_id=lid))
        db.commit()
    print(f"{len(buyers)} buyers, {total} interactions")


if __name__ == "__main__":
    main()