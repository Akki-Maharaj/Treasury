# Field definitions per category for interactive listing assistance
DEFAULT_FIELDS = [
    ("brand", "What is the brand or manufacturer?"),
    ("color", "What color is it?"),
    ("age", "How old is the item (e.g. 1 year, 6 months)?"),
]

CATEGORY_FIELDS = {
    "car": [
        ("brand", "What make/brand is the car (e.g. Toyota, Honda)?"),
        ("model", "What model is the car (e.g. Corolla, Civic)?"),
        ("year", "What is the manufacture year?"),
        ("mileage", "What is the current mileage (e.g. 45000 km)?"),
        ("fuelType", "What fuel type does it use (petrol, diesel, electric, hybrid, cng)?"),
        ("transmission", "Is it automatic or manual transmission?"),
    ],
    "electronics": [
        ("brand", "What is the brand (e.g. Apple, Samsung, Sony)?"),
        ("model", "What is the exact model name or number?"),
        ("age", "How long has it been used?"),
        ("warranty", "Is there remaining warranty (yes/no)?"),
    ],
    "ELECTRONICS": [
        ("brand", "What is the brand (e.g. Apple, Samsung, Sony)?"),
        ("model", "What is the exact model name or number?"),
        ("age", "How long has it been used?"),
        ("warranty", "Is there remaining warranty (yes/no)?"),
    ],
    "furniture": [
        ("material", "What material is it made of (e.g. wood, steel, leather)?"),
        ("color", "What color is it?"),
        ("size", "What are the dimensions or size?"),
        ("age", "How old is the piece?"),
    ],
    "HOME_KITCHEN_TOOLS": [
        ("material", "What material is it made of (e.g. steel, plastic, wood)?"),
        ("color", "What color is it?"),
        ("size", "What is the size or capacity?"),
        ("age", "How long has it been used?"),
    ],
    "BABY_PRODUCTS": [
        ("brand", "What is the brand?"),
        ("age", "What age group or how old is the item?"),
        ("color", "What color is it?"),
    ],
    "BEAUTY_HEALTH": [
        ("brand", "What is the brand?"),
        ("size", "What is the volume/weight/size?"),
        ("warranty", "Is it sealed / within expiry / under warranty?"),
    ],
    "CLOTHING_ACCESSORIES_JEWELLERY": [
        ("brand", "What is the brand or designer?"),
        ("size", "What size is it (e.g. M, L, 32, 10)?"),
        ("color", "What color is it?"),
        ("material", "What material/fabric is it?"),
    ],
    "GROCERY": [
        ("brand", "What is the brand?"),
        ("size", "What is the pack size or quantity?"),
        ("age", "What is the shelf life or expiry?"),
    ],
    "HOBBY_ARTS_STATIONERY": [
        ("brand", "What is the brand or maker?"),
        ("material", "What material or medium is it?"),
        ("color", "What color or theme is it?"),
    ],
    "PET_SUPPLIES": [
        ("brand", "What is the brand?"),
        ("size", "What pet size or product size is it for?"),
        ("material", "What material is it made from?"),
    ],
    "SPORTS_OUTDOOR": [
        ("brand", "What is the brand?"),
        ("size", "What size or specification is it?"),
        ("material", "What material is it made of?"),
        ("age", "How old is the equipment?"),
    ],
}
