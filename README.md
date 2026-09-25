# Treasury

**One man's trash is another man's treasure.**

Treasury is an OLX-style thrift marketplace with AI built into the core flows: listing a product and finding one. Sellers describe an item in plain text and the app detects the category, fills in the details it can, and asks only for what's missing. Buyers get a personalized feed and "similar items" powered by sentence embeddings.

**Live demo:** [https://treasury-1.onrender.com](https://treasury-1.onrender.com/)
(free hosting, so the first load after a quiet period can take a few seconds)

> Demo login: `buyer1@demo.com` / `demo1234`
> Listing creation is switched off on the public demo, but the AI assist on `/sell` still works.

<!-- Add 2-3 screenshots here: home feed, listing page, sell page with AI assist -->

## Features

**For sellers**
- **Category detection:** type a title and the category is suggested, with a confidence score, using a TF-IDF + Logistic Regression classifier.
- **Attribute extraction:** describe the item once ("2015 Swift, petrol, 40000 km, manual") and brand, year, mileage, fuel type, color, material and more are pulled out automatically.
- **Adaptive follow-up questions:** the app only asks for the details still missing for that category, one question at a time.
- **Frustration detection:** if the seller skips two questions in a row, it stops asking and says details can be added later.
- **Auto-generated description** from the collected details.

**For buyers**
- **Recommended for you:** a personalized row built from what you viewed and wishlisted.
- **Similar items** on every listing page.
- **Cold-start fallback:** new or logged-out users see what's popular.
- Search, category filters, pagination, wishlist, signup and login.

## How the AI works

| Feature | Approach |
|---|---|
| Category classification | TF-IDF (1-2 grams) + Logistic Regression in a scikit-learn pipeline. Trains in seconds on CPU and cannot make up categories, since its output is a fixed label set. Suggestions below a confidence threshold are dropped. |
| Attribute extraction | Rule-based (regex and keyword lists) with a per-category schema of fields to collect. Built so a trained NER model can replace it without changing the routes or UI. |
| Follow-up questions | Stateless endpoint: the browser sends the text, answers so far and skip count, and the server returns the filled fields, the next question, or "done". |
| Listing embeddings | `all-MiniLM-L6-v2` (sentence-transformers) over title, category and attribute values, normalized and stored as JSON in Postgres. |
| Recommendations | The user vector is a weighted mean of the embeddings of listings they interacted with (wishlist counts 3x, view 1x). Every listing is scored by cosine similarity with NumPy, and items the user already saw or owns are excluded. |
| Similar items | Cosine similarity between a listing's embedding and all others. |

The web app only loads stored embeddings and the small classifier at startup. It never loads PyTorch, which is why it runs on a small free instance.

## Tech stack

- **Backend:** FastAPI, SQLAlchemy, Jinja2 templates
- **Database and storage:** Supabase (PostgreSQL)
- **Auth:** signed session cookies with bcrypt password hashing
- **ML:** scikit-learn, sentence-transformers, NumPy
- **Frontend:** plain HTML, CSS and JavaScript (no build step)
- **Hosting:** Render

## Project structure

```
app/
  main.py            app setup, session middleware, demo lock
  db.py, models.py   SQLAlchemy engine and 7 tables
  auth.py            password hashing, current user
  routes/            auth, pages, wishlist, sell, ai endpoints
  ml/                category classifier, extraction, schema, description, recommender
  templates/, static/
ml-training/scripts/
  seed_listings_v2.py       demo listings from public datasets
  seed_interactions_v2.py   synthetic buyers with category and price tastes
  embed_listings.py         MiniLM embeddings for every listing
  train_category_clf.py     trains and saves the classifier
```

## Run it locally

```bash
git clone https://github.com/Akki-Maharaj/Treasury.git
cd Treasury
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
DATABASE_URL=postgresql://user:password@host:5432/postgres
SECRET_KEY=any-long-random-string
USE_SUPABASE_STORAGE=false
```

Start the app:

```bash
python -m uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000.

To rebuild the demo data and models (needs the datasets locally and `pip install -r requirements-train.txt`):

```bash
python ml-training/scripts/seed_listings_v2.py --reset
python ml-training/scripts/embed_listings.py
python ml-training/scripts/seed_interactions_v2.py --reset
python ml-training/scripts/train_category_clf.py
```

## Data

Listings are built from public Kaggle datasets (used car listings, car images, e-commerce product text and images, furniture and electronics data). Seller phone numbers are fake 8-digit numbers labelled as demo. Buyer interactions are **synthetic**: generated users with category and price preferences, used to demonstrate the recommender.

## Limitations and next steps

- Seeded titles are partly templated, so the classifier's scores on them look better than real-world accuracy would.
- Recommendations are content-based (embedding similarity). A learned two-tower ranking model is the planned next step.
- Attribute extraction is rule-based, and FLAN-T5 description generation is not built yet.
- New listings appear in recommendations after the embedding script runs again.
- Uploaded images on the free host are not persistent, which is one reason listing creation is disabled in the demo.
