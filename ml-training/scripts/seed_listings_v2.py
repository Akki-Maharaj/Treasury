# Seeds demo data through the app's own models, so column names always match the DB.
import sys, re, random, shutil
from pathlib import Path
import pandas as pd
from sqlalchemy import func

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))  # so "app" is importable from any working dir

from app.db import SessionLocal
from app.models import (User, Listing, ListingAttribute, ListingImage,
                        ListingEmbedding, Interaction, Wishlist)

DATA = ROOT  # folder holding car_pics/, ECOMMERCE_PRODUCT_IMAGES/, used car/, the CSVs
OUT = ROOT / "app" / "static" / "seed_images"
CONDITIONS = ["like new", "good", "good", "fair"]
COLORS = ["black", "white", "grey", "blue", "red", "brown", "green"]
random.seed(42)

BRANDS = {"audi": "Audi", "bmw": "BMW", "ford": "Ford", "toyota": "Toyota", "vw": "Volkswagen",
          "merc": "Mercedes-Benz", "skoda": "Skoda", "hyundi": "Hyundai", "vauxhall": "Vauxhall"}

# category: (item names, price range, brands), used to fabricate listings for the 9 image folders
CATS = {
    "BABY_PRODUCTS": (["stroller", "baby crib", "high chair", "baby carrier", "toy set", "bottle sterilizer"], (300, 4000), ["Chicco", "Graco", "Fisher-Price", "Mee Mee"]),
    "BEAUTY_HEALTH": (["hair dryer", "electric trimmer", "face massager", "weighing scale", "makeup kit", "BP monitor"], (300, 3500), ["Philips", "Braun", "Dr Trust", "Lakme"]),
    "CLOTHING_ACCESSORIES_JEWELLERY": (["leather jacket", "denim jeans", "sneakers", "wrist watch", "handbag", "silver necklace"], (300, 5000), ["Levis", "Zara", "Fossil", "Nike"]),
    "ELECTRONICS": (["bluetooth speaker", "tablet", "headphones", "smartwatch", "power bank", "gaming console"], (800, 25000), ["Sony", "Samsung", "boAt", "JBL"]),
    "GROCERY": (["dry fruits gift box", "tea gift set", "spice rack set", "coffee beans pack", "protein bars box", "olive oil bottles"], (200, 2500), ["Tata", "Nestle", "Britannia", "Amul"]),
    "HOBBY_ARTS_STATIONERY": (["acrylic paint set", "sketchbook bundle", "acoustic guitar", "calligraphy pen set", "board game", "jigsaw puzzle"], (200, 8000), ["Camlin", "Faber-Castell", "Yamaha", "Hasbro"]),
    "HOME_KITCHEN_TOOLS": (["pressure cooker", "mixer grinder", "air fryer", "cookware set", "drill machine", "toolbox set"], (500, 6000), ["Prestige", "Philips", "Bosch", "Pigeon"]),
    "PET_SUPPLIES": (["dog bed", "cat scratching post", "pet carrier", "aquarium tank", "dog leash set", "bird cage"], (300, 4000), ["Pedigree", "Whiskas", "Drools", "Kong"]),
    "SPORTS_OUTDOOR": (["cricket bat", "badminton racket set", "camping tent", "dumbbell set", "cycle", "football"], (300, 9000), ["Nivia", "Yonex", "SG", "Decathlon"]),
}

count = {"n": 0}
_files = {}


def money(v):
    # Handles "₹1,299", "$46.79", NaN -> float (0 if unparseable)
    s = re.sub(r"[^\d.]", "", str(v))
    try:
        return float(s) if s else 0.0
    except ValueError:
        return 0.0

def get_sellers(db, n=40):
    # Demo sellers with 8-digit fake phones so nobody real is ever contacted.
    # The DB column password_hash is NOT NULL, so give them a real bcrypt hash.
    import bcrypt
    pw = bcrypt.hashpw(b"demo1234", bcrypt.gensalt()).decode()  # hashed once, reused for all
    for i in range(1, n + 1):
        email = f"seller{i}@demo.com"
        if not db.query(User).filter_by(email=email).first():
            db.add(User(name=f"Seller {i}", email=email, password_hash=pw,
                        phone=str(random.randint(10**7, 10**8 - 1))))
    db.commit()
    return [i for (i,) in db.query(User.id).filter(User.email.like("seller%@demo.com"))]

def wipe(db):
    # Bulk deletes (fast) for everything belonging to demo sellers' listings
    sellers = [i for (i,) in db.query(User.id).filter(User.email.like("seller%@demo.com"))]
    ids = [i for (i,) in db.query(Listing.id).filter(Listing.user_id.in_(sellers))]
    for M in (ListingAttribute, ListingImage, ListingEmbedding, Interaction, Wishlist):
        db.query(M).filter(M.listing_id.in_(ids)).delete(synchronize_session=False)
    db.query(Listing).filter(Listing.id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    print(f"Deleted {len(ids)} old seeded listings")


def copy_img(src, group):
    # Copies into app/static so the site can serve it; returns the URL path
    d = OUT / group
    d.mkdir(parents=True, exist_ok=True)
    name = f"{src.parent.name}_{src.name}".replace(" ", "_")
    if not (d / name).exists():
        shutil.copy2(src, d / name)
    return f"/static/seed_images/{group}/{name}"


def pick_images(folder, group):
    # 2-3 images from ONE folder, so a listing's photos look consistent
    if not folder.exists():
        return []
    if folder not in _files:
        _files[folder] = [p for p in folder.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
    imgs = _files[folder]
    return [copy_img(p, group) for p in random.sample(imgs, min(random.randint(2, 3), len(imgs)))]


def add_listing(db, seller_id, title, category, price, condition, attrs, image_urls):
    l = Listing(user_id=seller_id, title=title[:200], category=category, price=round(float(price), 2),
                condition=condition, status="active", description=f"{title}. Condition: {condition}.")
    l.attributes = [ListingAttribute(key=k, value=str(v)) for k, v in attrs.items()]
    l.images = [ListingImage(image_url=u, is_primary=(i == 0)) for i, u in enumerate(image_urls)]
    db.add(l)
    count["n"] += 1
    if count["n"] % 50 == 0:
        db.commit()
        print(f"  {count['n']} listings...")


def seed_cars(db, sellers):
    root = DATA / "car_pics" / "car_data" / "car_data" / "train"
    folders = [d for d in root.iterdir() if d.is_dir()]
    for key, brand in BRANDS.items():
        df = pd.read_csv(DATA / "used car" / f"{key}.csv", encoding_errors="replace")
        df.columns = ["tax" if c.strip().lower().startswith("tax") else c.strip() for c in df.columns]
        df = df.dropna(subset=["model", "year", "price", "mileage"])
        for _, r in df.sample(min(34, len(df)), random_state=1).iterrows():
            model = str(r["model"]).strip()
            same = [d for d in folders if d.name.lower().startswith(brand.lower())]
            close = [d for d in same if model.lower() in d.name.lower()]
            folder = random.choice(close or same or folders)
            miles = int(r["mileage"])
            cond = "like new" if miles < 20000 else "good" if miles < 60000 else "fair"
            attrs = {c: r[c] for c in ["year", "mileage", "transmission", "fuelType", "tax", "mpg", "engineSize"] if c in df.columns}
            attrs["brand"] = brand
            # x100 = rough GBP -> INR so all prices look like one currency
            add_listing(db, random.choice(sellers), f"{brand} {model} {int(r['year'])}", "car",
                        float(r["price"]) * 100, cond, attrs, pick_images(folder, "cars"))


def seed_electronics(db, sellers):
    df = pd.read_csv(DATA / "amazon_electronics_product.csv", encoding_errors="replace", on_bad_lines="skip")
    df = df[df["image"].astype(str).str.startswith("http")].dropna(subset=["name"])
    for _, r in df.sample(min(150, len(df)), random_state=1).iterrows():
        price = money(r["discount_price"]) or money(r["actual_price"])
        if price > 0:  # real hosted image URL, stored as is
            add_listing(db, random.choice(sellers), str(r["name"]), "ELECTRONICS", price,
                        random.choice(CONDITIONS), {"type": r["sub_category"]}, [r["image"]])


def seed_furniture(db, sellers):
    df = pd.read_csv(DATA / "ecommerce_furniture_dataset_2024.csv", encoding_errors="replace").dropna(subset=["productTitle"])
    pool = DATA / "ECOMMERCE_PRODUCT_IMAGES" / "train" / "HOME_KITCHEN_TOOLS"
    for _, r in df.sample(min(100, len(df)), random_state=1).iterrows():
        price = money(r["price"]) * 80  # rough USD -> INR
        if price > 0:
            add_listing(db, random.choice(sellers), str(r["productTitle"]), "furniture", price,
                        random.choice(CONDITIONS), {}, pick_images(pool, "furniture"))


def seed_categories(db, sellers):
    for cat, (items, (lo, hi), brands) in CATS.items():
        folder = DATA / "ECOMMERCE_PRODUCT_IMAGES" / "train" / cat
        for _ in range(40):
            brand, item = random.choice(brands), random.choice(items)
            attrs = {"brand": brand, "color": random.choice(COLORS), "age": f"{random.randint(1, 36)} months"}
            add_listing(db, random.choice(sellers), f"{brand} {item.title()}", cat,
                        random.randint(lo, hi) // 50 * 50, random.choice(CONDITIONS), attrs,
                        pick_images(folder, cat.lower()))


def main():
    db = SessionLocal()
    if "--reset" in sys.argv:
        wipe(db)
    sellers = get_sellers(db)
    if db.query(Listing).filter(Listing.user_id.in_(sellers)).count() > 0:
        print("Already seeded. Run again with --reset to redo it.")
        return
    for fn in (seed_cars, seed_electronics, seed_furniture, seed_categories):
        print(f"Running {fn.__name__}...")
        fn(db, sellers)
    db.commit()
    for cat, n in db.query(Listing.category, func.count()).group_by(Listing.category).all():
        print(f"{cat}: {n}")
    print("Total:", count["n"])


if __name__ == "__main__":
    main()