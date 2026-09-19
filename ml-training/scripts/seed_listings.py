"""
Seed Listings Script
--------------------
Fabricates and seeds listings into PostgreSQL for Cars and General Products.
Includes toggleable Supabase Storage upload or local storage fallback,
safe re-run / --reset support, and listing_embeddings initialization.
"""

import os
import sys
import re
import glob
import uuid
import random
import shutil
import argparse
from pathlib import Path
import pandas as pd
import pandas as pd

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    psycopg2 = None

DATABASE_URL = os.getenv("DATABASE_URL")
USE_SUPABASE_STORAGE = os.getenv("USE_SUPABASE_STORAGE", "false").strip().lower() in ("true", "1", "yes")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "listing-images")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOCAL_IMAGE_DIR = BASE_DIR / "seed-data" / "seed_images"

supabase_client = None
if USE_SUPABASE_STORAGE:
    try:
        from supabase import create_client
        if SUPABASE_URL and SUPABASE_KEY:
            supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        else:
            print("[WARN] USE_SUPABASE_STORAGE is true, but SUPABASE_URL or SUPABASE_KEY is missing. Falling back to local storage.")
    except Exception as e:
        print(f"[WARN] Failed to initialize Supabase client ({e}). Falling back to local storage.")


# 1-line: Ensure database tables exist before seeding.
def ensure_schema(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                phone VARCHAR(50),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS listings (
                id UUID PRIMARY KEY,
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR(500) NOT NULL,
                description TEXT,
                category VARCHAR(100) NOT NULL,
                price NUMERIC(12, 2) NOT NULL,
                condition VARCHAR(50) NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'active',
                is_seed BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS listing_attributes (
                id UUID PRIMARY KEY,
                listing_id UUID REFERENCES listings(id) ON DELETE CASCADE,
                key VARCHAR(100) NOT NULL,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS listing_images (
                id UUID PRIMARY KEY,
                listing_id UUID REFERENCES listings(id) ON DELETE CASCADE,
                image_url TEXT NOT NULL,
                is_primary BOOLEAN DEFAULT FALSE
            );

            CREATE TABLE IF NOT EXISTS listing_embeddings (
                id UUID PRIMARY KEY,
                listing_id UUID UNIQUE REFERENCES listings(id) ON DELETE CASCADE,
                embedding_vector JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_listings_is_seed ON listings(is_seed);
            CREATE INDEX IF NOT EXISTS idx_listings_category ON listings(category);
        """)
    conn.commit()


# 1-line: Reset or truncate existing seed data if --reset is passed.
def reset_seed_data(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM listings WHERE is_seed = TRUE;")
        count = cur.fetchone()[0]
        if count > 0:
            print(f"[RESET] Removing {count} existing seeded listings and related records...")
            cur.execute("DELETE FROM listings WHERE is_seed = TRUE;")
            conn.commit()
            print("[RESET] Cleaned up previous seed listings.")


# 1-line: Check whether seed data has already been populated.
def is_already_seeded(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM listings WHERE is_seed = TRUE;")
        return cur.fetchone()[0] > 0


# 1-line: Fabricate and insert a random seller user or retrieve one.
def get_or_create_user(conn, user_cache):
    if user_cache and random.random() < 0.7:
        return random.choice(user_cache)
    
    user_id = str(uuid.uuid4())
    first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Sam", "Chris", "Pat", "Riley", "Casey", "Avery", "David", "Emma", "Liam", "Sophia"]
    last_names = ["Smith", "Johnson", "Brown", "Taylor", "Miller", "Wilson", "Moore", "Anderson", "Thomas", "Jackson"]
    full_name = f"{random.choice(first_names)} {random.choice(last_names)}"
    email = f"{full_name.lower().replace(' ', '.')}.{uuid.uuid4().hex[:6]}@example.com"
    phone = f"{random.randint(60000000, 99999999)}"
    
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (id, name, email, phone) VALUES (%s, %s, %s, %s);",
            (user_id, full_name, email, phone)
        )
    user_cache.append(user_id)
    return user_id


# 1-line: Store an image locally or upload it to Supabase Storage, returning the path or URL.
def store_image(source_path, subfolder):
    source = Path(source_path)
    if not source.exists():
        return None

    filename = f"{uuid.uuid4().hex}_{source.name}"

    if USE_SUPABASE_STORAGE and supabase_client:
        try:
            storage_path = f"{subfolder}/{filename}"
            with open(source, "rb") as f:
                file_bytes = f.read()
            res = supabase_client.storage.from_(SUPABASE_BUCKET).upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": "image/jpeg"}
            )
            public_url = supabase_client.storage.from_(SUPABASE_BUCKET).get_public_url(storage_path)
            return public_url
        except Exception as e:
            # Fallback to local if storage upload fails
            pass

    # Local fallback
    dest_dir = LOCAL_IMAGE_DIR / subfolder
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename
    try:
        shutil.copyfile(source, dest_path)
        # Store relative local path
        return str(Path("seed-data") / "seed_images" / subfolder / filename).replace("\\", "/")
    except Exception as e:
        return None


# 1-line: Clean and parse numeric price strings into floats.
def parse_price(val, default_min=10.0, default_max=500.0):
    if pd.isna(val):
        return round(random.uniform(default_min, default_max), 2)
    s = str(val).replace(",", "").replace("$", "").replace("₹", "").strip()
    match = re.search(r"[-+]?\d*\.\d+|\d+", s)
    if match:
        try:
            return round(float(match.group()), 2)
        except ValueError:
            pass
    return round(random.uniform(default_min, default_max), 2)


# 1-line: Find matching car image files by matching brand, model, and year against train folders.
def find_car_images(brand, model, year, car_folders, all_car_folders):
    norm_brand = brand.lower().replace(" ", "")
    norm_model = model.lower().replace(" ", "")
    norm_year = str(year).strip()

    best_match = None
    brand_matches = []

    for folder in all_car_folders:
        folder_name = folder.name.lower()
        if norm_brand in folder_name:
            brand_matches.append(folder)
            if norm_model in folder_name.replace(" ", "") and norm_year in folder_name:
                best_match = folder
                break
            elif norm_model in folder_name.replace(" ", "") and not best_match:
                best_match = folder

    selected_folder = best_match or (random.choice(brand_matches) if brand_matches else (random.choice(all_car_folders) if all_car_folders else None))
    
    if not selected_folder:
        return []

    images = [p for p in selected_folder.glob("*.jpg")] + [p for p in selected_folder.glob("*.jpeg")]
    sample_size = min(len(images), random.randint(2, 3))
    return random.sample(images, sample_size) if images else []


# 1-line: Load and sample used car listings from valid brand CSV files.
def seed_cars(conn, user_cache, stats, sample_target=300):
    used_car_dir = BASE_DIR / "used car"
    if not used_car_dir.exists():
        print("[WARN] 'used car' directory not found.")
        return

    csv_files = [f for f in used_car_dir.glob("*.csv") if not f.name.lower().startswith("unclean")]
    if not csv_files:
        print("[WARN] No clean car CSV files found.")
        return

    car_train_dir = BASE_DIR / "car_pics" / "car_data" / "car_data" / "train"
    all_car_folders = [p for p in car_train_dir.iterdir() if p.is_dir()] if car_train_dir.exists() else []

    all_rows = []
    for f in csv_files:
        brand = f.stem.replace(".csv", "").strip().capitalize()
        if brand.lower() == "merc":
            brand = "Mercedes-Benz"
        elif brand.lower() == "vw":
            brand = "Volkswagen"
        elif brand.lower() == "hyundi":
            brand = "Hyundai"
        elif brand.lower() in ("cclass", "focus"):
            brand = "Mercedes-Benz" if brand.lower() == "cclass" else "Ford"

        try:
            df = pd.read_csv(f)
            df["brand"] = brand
            all_rows.append(df)
        except Exception as e:
            print(f"[WARN] Error reading {f.name}: {e}")

    if not all_rows:
        return

    combined = pd.concat(all_rows, ignore_index=True)
    sampled = combined.sample(n=min(len(combined), sample_target), random_state=42)

    print(f"[SEED] Processing {len(sampled)} car listings...")
    for idx, (_, row) in enumerate(sampled.iterrows(), start=1):
        brand = str(row.get("brand", "Car"))
        model = str(row.get("model", "")).strip()
        year = int(row["year"]) if pd.notna(row.get("year")) else 2018
        price = parse_price(row.get("price"), 5000.0, 45000.0)
        mileage = float(row.get("mileage", 35000)) if pd.notna(row.get("mileage")) else 35000

        # Condition logic based on mileage
        if mileage < 20000:
            condition = "like new"
        elif mileage < 60000:
            condition = "good"
        else:
            condition = "fair"

        title = f"{brand} {model} {year}".strip()
        user_id = get_or_create_user(conn, user_cache)
        listing_id = str(uuid.uuid4())

        # Insert listing
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO listings (id, user_id, title, description, category, price, condition, status, is_seed)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE);
                """,
                (listing_id, user_id, title, f"Well maintained {title} with {int(mileage):,} miles.", "car", price, condition, "active")
            )

            # Insert listing_attributes
            attributes = [
                ("mileage", str(row.get("mileage", ""))),
                ("transmission", str(row.get("transmission", ""))),
                ("fuelType", str(row.get("fuelType", ""))),
                ("tax", str(row.get("tax", ""))),
                ("mpg", str(row.get("mpg", ""))),
                ("engineSize", str(row.get("engineSize", "")))
            ]
            for k, v in attributes:
                if v and v != "nan":
                    cur.execute(
                        "INSERT INTO listing_attributes (id, listing_id, key, value) VALUES (%s, %s, %s, %s);",
                        (str(uuid.uuid4()), listing_id, k, v)
                    )

            # Images
            car_imgs = find_car_images(brand, model, year, all_car_folders, all_car_folders)
            for img_idx, img_file in enumerate(car_imgs):
                stored_url = store_image(img_file, "cars")
                if stored_url:
                    cur.execute(
                        "INSERT INTO listing_images (id, listing_id, image_url, is_primary) VALUES (%s, %s, %s, %s);",
                        (str(uuid.uuid4()), listing_id, stored_url, (img_idx == 0))
                    )
                    stats["images"] += 1

            # listing_embeddings (placeholder)
            cur.execute(
                "INSERT INTO listing_embeddings (id, listing_id, embedding_vector) VALUES (%s, %s, NULL);",
                (str(uuid.uuid4()), listing_id)
            )

        conn.commit()
        stats["categories"]["car"] = stats["categories"].get("car", 0) + 1
        stats["total_listings"] += 1

        if stats["total_listings"] % 50 == 0:
            print(f"[PROGRESS] Seeded {stats['total_listings']} listings total...")


# 1-line: Sample and seed electronics products from amazon_electronics_product.csv.
def seed_amazon_electronics(conn, user_cache, stats, sample_target=150):
    csv_path = BASE_DIR / "amazon_electronics_product.csv"
    if not csv_path.exists():
        print("[WARN] amazon_electronics_product.csv not found.")
        return

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"[WARN] Error reading {csv_path.name}: {e}")
        return

    sampled = df.sample(n=min(len(df), sample_target), random_state=42)
    print(f"[SEED] Processing {len(sampled)} Amazon electronics listings...")

    for _, row in sampled.iterrows():
        name = str(row.get("name", "Electronic Device")).strip()
        category = str(row.get("main_category", "electronics")).strip().lower()
        if not category or category == "nan":
            category = "electronics"
        price = parse_price(row.get("discount_price") or row.get("actual_price"), 15.0, 800.0)
        user_id = get_or_create_user(conn, user_cache)
        listing_id = str(uuid.uuid4())
        image_url = str(row.get("image", "")).strip()

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO listings (id, user_id, title, description, category, price, condition, status, is_seed)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE);
                """,
                (listing_id, user_id, name[:490], name, category, price, "new", "active")
            )

            # Insert ratings attribute if available
            if pd.notna(row.get("ratings")):
                cur.execute(
                    "INSERT INTO listing_attributes (id, listing_id, key, value) VALUES (%s, %s, %s, %s);",
                    (str(uuid.uuid4()), listing_id, "ratings", str(row.get("ratings")))
                )

            # Direct hosted image link
            if image_url and image_url != "nan" and image_url.startswith("http"):
                cur.execute(
                    "INSERT INTO listing_images (id, listing_id, image_url, is_primary) VALUES (%s, %s, %s, TRUE);",
                    (str(uuid.uuid4()), listing_id, image_url)
                )
                stats["images"] += 1

            # listing_embeddings
            cur.execute(
                "INSERT INTO listing_embeddings (id, listing_id, embedding_vector) VALUES (%s, %s, NULL);",
                (str(uuid.uuid4()), listing_id)
            )

        conn.commit()
        stats["categories"][category] = stats["categories"].get(category, 0) + 1
        stats["total_listings"] += 1

        if stats["total_listings"] % 50 == 0:
            print(f"[PROGRESS] Seeded {stats['total_listings']} listings total...")


# 1-line: Sample and seed furniture products using ecommerce_furniture_dataset_2024.csv.
def seed_furniture(conn, user_cache, stats, sample_target=100):
    csv_path = BASE_DIR / "ecommerce_furniture_dataset_2024.csv"
    if not csv_path.exists():
        print("[WARN] ecommerce_furniture_dataset_2024.csv not found.")
        return

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"[WARN] Error reading {csv_path.name}: {e}")
        return

    # Image pool from HOME_KITCHEN_TOOLS
    furniture_img_dir = BASE_DIR / "ECOMMERCE_PRODUCT_IMAGES" / "train" / "HOME_KITCHEN_TOOLS"
    img_pool = [p for p in furniture_img_dir.glob("*.jpeg")] + [p for p in furniture_img_dir.glob("*.jpg")] if furniture_img_dir.exists() else []

    sampled = df.sample(n=min(len(df), sample_target), random_state=42)
    print(f"[SEED] Processing {len(sampled)} furniture listings...")

    for _, row in sampled.iterrows():
        title = str(row.get("productTitle", "Modern Furniture Piece")).strip()
        price = parse_price(row.get("price"), 25.0, 450.0)
        user_id = get_or_create_user(conn, user_cache)
        listing_id = str(uuid.uuid4())

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO listings (id, user_id, title, description, category, price, condition, status, is_seed)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE);
                """,
                (listing_id, user_id, title[:490], title, "furniture", price, "like new", "active")
            )

            # Assign 2-3 images from pool
            if img_pool:
                sample_count = min(len(img_pool), random.randint(2, 3))
                selected_imgs = random.sample(img_pool, sample_count)
                for img_idx, img_path in enumerate(selected_imgs):
                    stored_url = store_image(img_path, "furniture")
                    if stored_url:
                        cur.execute(
                            "INSERT INTO listing_images (id, listing_id, image_url, is_primary) VALUES (%s, %s, %s, %s);",
                            (str(uuid.uuid4()), listing_id, stored_url, (img_idx == 0))
                        )
                        stats["images"] += 1

            # listing_embeddings
            cur.execute(
                "INSERT INTO listing_embeddings (id, listing_id, embedding_vector) VALUES (%s, %s, NULL);",
                (str(uuid.uuid4()), listing_id)
            )

        conn.commit()
        stats["categories"]["furniture"] = stats["categories"].get("furniture", 0) + 1
        stats["total_listings"] += 1

        if stats["total_listings"] % 50 == 0:
            print(f"[PROGRESS] Seeded {stats['total_listings']} listings total...")


# 1-line: Fabricate realistic category-specific product listings using ECOMMERCE_PRODUCT_IMAGES.
def seed_ecommerce_categories(conn, user_cache, stats, per_category=40):
    ecom_train_dir = BASE_DIR / "ECOMMERCE_PRODUCT_IMAGES" / "train"
    if not ecom_train_dir.exists():
        print("[WARN] ECOMMERCE_PRODUCT_IMAGES/train not found.")
        return

    category_samples = {
        "BABY_PRODUCTS": [
            ("Ergonomic Soft Baby Carrier", 29.99), ("Silicone Baby Teething Toys Set", 12.50),
            ("Convertible Baby Stroller Lightweight", 129.99), ("Organic Cotton Baby Swaddle Blankets", 21.00),
            ("Electric Baby Bottle Warmer & Sterilizer", 38.49), ("Baby High Chair with Removable Tray", 74.99),
            ("Infant Safety Monitor HD Audio & Video", 69.95), ("Natural Wooden Baby Crib Mobile", 18.25),
            ("Soft Plush Baby Musical Toy", 14.99), ("Non-Toxic Diaper Rash Relief Cream", 9.99)
        ],
        "BEAUTY_HEALTH": [
            ("Hydrating Hyaluronic Acid Facial Serum", 19.99), ("Volumizing Biotin Hair Conditioner", 15.50),
            ("Electric Sonic Toothbrush Rechargeable", 39.99), ("Pure Organic Cold-Pressed Argan Oil", 16.20),
            ("Deep Cleansing Clay Face Mask", 13.99), ("Aromatherapy Essential Oil Diffuser", 24.50),
            ("SPF 50 Mineral Daily Sunscreen", 17.80), ("Professional Nail Grooming & Pedicure Kit", 22.00)
        ],
        "CLOTHING_ACCESSORIES_JEWELLERY": [
            ("Classic Leather Bifold Wallet", 28.00), ("Minimalist Stainless Steel Watch", 65.00),
            ("Sterling Silver Pendant Necklace", 45.00), ("Polarized Aviator Sunglasses UV400", 25.50),
            ("Breathable Cotton Crewneck Sweatshirt", 34.00), ("Genuine Leather Dress Belt", 22.90),
            ("Gold Plated Hoop Earrings Set", 19.99), ("Vintage Denim Jacket Unisex", 58.00)
        ],
        "ELECTRONICS": [
            ("Wireless Noise Cancelling Earbuds", 49.99), ("Ultra-Slim Fast Wireless Charger Pad", 18.99),
            ("Portable Bluetooth Waterproof Speaker", 35.50), ("Mechanical Gaming Keyboard RGB Backlit", 59.99),
            ("Dual Band WiFi 6 Range Extender", 42.00), ("Ergonomic Wireless Optical Mouse", 19.50)
        ],
        "GROCERY": [
            ("Organic Extra Virgin Olive Oil 1L", 18.99), ("Raw Wildflower Honey Glass Jar", 12.49),
            ("Artisan Whole Bean Dark Roast Coffee", 14.99), ("Organic Roasted California Almonds 500g", 11.25),
            ("Pure Maple Syrup Grade A 500ml", 13.80), ("Organic Green Tea Matcha Powder", 16.50)
        ],
        "HOBBY_ARTS_STATIONERY": [
            ("Dual Tip Acrylic Paint Markers 24ct", 22.50), ("Hardcover Watercolor Journal 300gsm", 17.99),
            ("Professional Graphite Sketching Pencil Set", 14.25), ("Calligraphy Dip Pen and Ink Set", 26.00),
            ("Self-Healing Rotary Cutting Mat", 15.99), ("Vibrant Oil Pastel Colors 36-pack", 19.50)
        ],
        "HOME_KITCHEN_TOOLS": [
            ("Stainless Steel Chef Knife 8-Inch", 32.99), ("Cast Iron Skillet Pre-Seasoned 10-Inch", 27.50),
            ("Non-Stick Heavy Duty Silicone Spatula Set", 14.00), ("Digital Food Kitchen Scale Precise", 15.99),
            ("Stainless Steel Mixing Bowls Set of 5", 28.49), ("Electric Milk Frother Handheld", 12.99)
        ],
        "PET_SUPPLIES": [
            ("Orthopedic Memory Foam Dog Bed Large", 55.00), ("Interactive Laser Feather Cat Toy", 13.50),
            ("Retractable Dog Leash with LED Light", 19.99), ("Stainless Steel Dual Pet Bowls Non-Spill", 16.75),
            ("Natural Grain-Free Salmon Dog Treats", 11.99), ("Self-Cleaning Slicker Brush for Pets", 14.25)
        ],
        "SPORTS_OUTDOOR": [
            ("High Density Non-Slip Yoga Mat 6mm", 24.99), ("Insulated Stainless Steel Water Bottle 32oz", 21.50),
            ("Resistance Bands Exercise Set 5-Levels", 18.00), ("Compact Camping Hammock with Straps", 29.95),
            ("LED Rechargeable Headlamp Waterproof", 17.50), ("Lightweight Hiking Backpack 30L", 39.99)
        ]
    }

    # Pre-build image pool per category in memory to avoid repetitive disk traversal
    category_dirs = [d for d in ecom_train_dir.iterdir() if d.is_dir()]
    img_pools = {}
    for cdir in category_dirs:
        img_pools[cdir.name] = [p for p in cdir.glob("*.jpeg")] + [p for p in cdir.glob("*.jpg")]

    for cdir in category_dirs:
        cat_name = cdir.name
        clean_cat = cat_name.lower().replace("_", " ")
        pool = img_pools.get(cat_name, [])
        templates = category_samples.get(cat_name, [("Product Item", 20.00)])

        print(f"[SEED] Processing ~{per_category} listings for {cat_name}...")
        for i in range(per_category):
            base_title, base_price = templates[i % len(templates)]
            variant_suffix = f"- Series {i + 1}" if i >= len(templates) else ""
            title = f"{base_title} {variant_suffix}".strip()
            price = round(base_price * random.uniform(0.9, 1.15), 2)
            user_id = get_or_create_user(conn, user_cache)
            listing_id = str(uuid.uuid4())

            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO listings (id, user_id, title, description, category, price, condition, status, is_seed)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE);
                    """,
                    (listing_id, user_id, title, f"High quality {title} in excellent condition.", clean_cat, price, "new", "active")
                )

                if pool:
                    sample_count = min(len(pool), random.randint(2, 3))
                    chosen_imgs = random.sample(pool, sample_count)
                    for img_idx, img_path in enumerate(chosen_imgs):
                        stored_url = store_image(img_path, cat_name.lower())
                        if stored_url:
                            cur.execute(
                                "INSERT INTO listing_images (id, listing_id, image_url, is_primary) VALUES (%s, %s, %s, %s);",
                                (str(uuid.uuid4()), listing_id, stored_url, (img_idx == 0))
                            )
                            stats["images"] += 1

                # listing_embeddings
                cur.execute(
                    "INSERT INTO listing_embeddings (id, listing_id, embedding_vector) VALUES (%s, %s, NULL);",
                    (str(uuid.uuid4()), listing_id)
                )

            conn.commit()
            stats["categories"][clean_cat] = stats["categories"].get(clean_cat, 0) + 1
            stats["total_listings"] += 1

            if stats["total_listings"] % 50 == 0:
                print(f"[PROGRESS] Seeded {stats['total_listings']} listings total...")


# 1-line: Print comprehensive seed run summary.
def print_summary(stats, user_cache):
    print("\n" + "=" * 55)
    print("           SEEDING PROCESS COMPLETE SUMMARY           ")
    print("=" * 55)
    print(f"Total Listings Created:    {stats['total_listings']}")
    print(f"Total Users Created:       {len(user_cache)}")
    print(f"Total Images Saved/Linked: {stats['images']}")
    print("-" * 55)
    print("Listings per Category:")
    for cat, count in sorted(stats["categories"].items(), key=lambda x: x[1], reverse=True):
        print(f"  - {cat.ljust(32)}: {count}")
    print("=" * 55)
    if USE_SUPABASE_STORAGE and supabase_client:
        print(f"Image Storage: Supabase Storage Bucket '{SUPABASE_BUCKET}'")
    else:
        print(f"Image Storage: Local files at {LOCAL_IMAGE_DIR}")
    print("=" * 55 + "\n")


# 1-line: Main CLI entrypoint for orchestrating the database connection and seeding pipeline.
def main():
    parser = argparse.ArgumentParser(description="Seed Treasury listings into PostgreSQL database.")
    parser.add_argument("--reset", action="store_true", help="Truncate / clear existing seed listings before seeding")
    parser.add_argument("--car-sample", type=int, default=300, help="Number of car rows to seed (default: 300)")
    parser.add_argument("--amazon-sample", type=int, default=150, help="Number of Amazon rows to seed (default: 150)")
    parser.add_argument("--furniture-sample", type=int, default=100, help="Number of furniture rows to seed (default: 100)")
    parser.add_argument("--category-sample", type=int, default=40, help="Listings per ecommerce category (default: 40)")
    args = parser.parse_args()

    if not DATABASE_URL:
        print("\n[ERROR] DATABASE_URL is not set in environment or .env file.")
        print("Please configure DATABASE_URL=postgresql://user:password@host:port/dbname in your .env file.\n")
        sys.exit(1)

    if psycopg2 is None:
        print("\n[ERROR] psycopg2 is not installed. Please run: pip install psycopg2-binary\n")
        sys.exit(1)

    try:
        conn = psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"\n[ERROR] Could not connect to PostgreSQL with DATABASE_URL: {e}\n")
        sys.exit(1)

    print("\n[INIT] Connected to PostgreSQL successfully.")
    ensure_schema(conn)

    if args.reset:
        reset_seed_data(conn)
    elif is_already_seeded(conn):
        print("[NOTICE] Seed data already exists in database. To re-seed, run with the --reset flag.")
        print("Example: python ml-training/scripts/seed_listings.py --reset\n")
        conn.close()
        return

    user_cache = []
    stats = {
        "total_listings": 0,
        "images": 0,
        "categories": {}
    }

    try:
        seed_cars(conn, user_cache, stats, sample_target=args.car_sample)
        seed_amazon_electronics(conn, user_cache, stats, sample_target=args.amazon_sample)
        seed_furniture(conn, user_cache, stats, sample_target=args.furniture_sample)
        seed_ecommerce_categories(conn, user_cache, stats, per_category=args.category_sample)
        print_summary(stats, user_cache)
    except Exception as e:
        print(f"\n[ERROR] Seeding process interrupted by error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
