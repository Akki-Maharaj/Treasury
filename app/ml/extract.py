import re
from app.ml.schema import CATEGORY_FIELDS, DEFAULT_FIELDS

# Common brands across cars, phones, laptops, furniture, sports
BRANDS = [
    # Cars
    "toyota", "honda", "ford", "bmw", "mercedes", "audi", "hyundai", "nissan",
    "volkswagen", "chevrolet", "kia", "subaru", "tesla", "mazda", "volvo",
    "jeep", "suzuki", "renault", "skoda", "porsche", "lexus",
    # Tech / Electronics
    "apple", "samsung", "sony", "dell", "hp", "lenovo", "asus", "acer",
    "lg", "google", "oneplus", "xiaomi", "bose", "canon", "nikon", "microsoft",
    "logitech", "motorola", "intel", "amd", "nvidia", "panasonic",
    # Furniture / Home
    "ikea", "ashley", "herman miller", "steelcase", "west elm", "pottery barn",
    "cb2", "wayfair", "dyson", "philips", "bosch",
    # Sports / Apparel
    "nike", "adidas", "puma", "under armour", "reebok", "wilson", "decathlon",
    "trek", "giant", "shimano", "spalding", "columbia", "patagonia",
]

COLORS = [
    "black", "white", "silver", "grey", "gray", "red", "blue", "green",
    "yellow", "brown", "beige", "orange", "gold", "navy", "maroon", "pink", "purple"
]

MATERIALS = [
    "wood", "steel", "plastic", "leather", "glass", "fabric", "metal",
    "aluminum", "cotton", "ceramic", "velvet", "iron", "mesh"
]


def extract_attributes(text: str, category: str) -> dict:
    attrs = {}
    lower_text = f" {text.lower()} "

    # Year (19xx or 20xx)
    m_year = re.search(r"\b(19\d{2}|20\d{2})\b", text)
    if m_year:
        attrs["year"] = m_year.group(1)

    # Mileage (number + km/kms/miles)
    m_mileage = re.search(r"(\b\d{1,3}(?:,\d{3})*|\b\d+)\s*(k\.?m\.?s?|km|kms|kilometers?|miles?|mi)\b", lower_text)
    if m_mileage:
        num = m_mileage.group(1).replace(",", "")
        unit = "km" if "m" in m_mileage.group(2) and "mile" not in m_mileage.group(2) else "miles"
        attrs["mileage"] = f"{num} {unit}"

    # Fuel Type
    m_fuel = re.search(r"\b(petrol|gasoline|diesel|electric|hybrid|cng)\b", lower_text)
    if m_fuel:
        attrs["fuelType"] = m_fuel.group(1).capitalize()

    # Transmission
    m_trans = re.search(r"\b(manual|automatic|auto)\b", lower_text)
    if m_trans:
        val = m_trans.group(1)
        attrs["transmission"] = "Automatic" if val in ("automatic", "auto") else "Manual"

    # Age ("2 years old", "6 months old", "used for 3 months")
    m_age = re.search(r"(\b\d+\s*(?:years?|yrs?|months?|mos?)(?:\s*old)?)\b", lower_text)
    if m_age:
        attrs["age"] = m_age.group(1).strip()

    # Brand
    for b in sorted(BRANDS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(b)}\b", lower_text):
            attrs["brand"] = b.title()
            break

    # Color
    for c in COLORS:
        if re.search(rf"\b{re.escape(c)}\b", lower_text):
            attrs["color"] = c.capitalize()
            break

    # Material
    for m in MATERIALS:
        if re.search(rf"\b{re.escape(m)}\b", lower_text):
            attrs["material"] = m.capitalize()
            break

    # Warranty (yes/no phrases)
    if re.search(r"\b(under warranty|with warranty|warranty valid|has warranty|1 year warranty|2 year warranty)\b", lower_text):
        attrs["warranty"] = "Yes"
    elif re.search(r"\b(no warranty|warranty expired|out of warranty)\b", lower_text):
        attrs["warranty"] = "No"

    # Filter to only fields allowed by category schema
    fields = CATEGORY_FIELDS.get(category, DEFAULT_FIELDS)
    allowed_keys = {key for key, _ in fields}
    return {k: v for k, v in attrs.items() if k in allowed_keys}
