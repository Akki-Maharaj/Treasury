# Simple template-based sentence builder for item descriptions.
# Keep the function signature stable for future FLAN-T5 model drop-in.
def generate_description(title: str, category: str, attrs: dict) -> str:
    sentences = []
    
    # Opening sentence
    clean_title = title.strip() if title else ""
    brand = attrs.get("brand")
    model = attrs.get("model")
    year = attrs.get("year")
    
    if clean_title:
        sentences.append(f"Up for sale is this {clean_title}.")
    elif brand or model or year:
        name_parts = [p for p in [year, brand, model] if p]
        sentences.append(f"Up for sale is this {' '.join(name_parts)}.")
    else:
        cat_name = (category or "general").replace("_", " ").lower()
        sentences.append(f"Up for sale is a great quality item in {cat_name}.")

    # Specification highlights
    specs = []
    if "age" in attrs:
        specs.append(f"used for {attrs['age']}")
    if "mileage" in attrs:
        specs.append(f"with {attrs['mileage']}")
    if "fuelType" in attrs:
        specs.append(f"{attrs['fuelType']} engine")
    if "transmission" in attrs:
        specs.append(f"{attrs['transmission']} transmission")
    if "material" in attrs:
        specs.append(f"crafted from {attrs['material'].lower()}")
    if "color" in attrs:
        specs.append(f"in {attrs['color'].lower()} finish")
    if "size" in attrs:
        specs.append(f"size/dimensions: {attrs['size']}")
    if "warranty" in attrs:
        specs.append(f"warranty: {attrs['warranty']}")

    if specs:
        spec_text = ", ".join(specs)
        sentences.append(f"Features and specifications include: {spec_text}.")

    sentences.append("Well-maintained and ready for its next owner. Feel free to reach out with any questions!")
    return " ".join(sentences)
