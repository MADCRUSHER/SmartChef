import os
import random
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
import requests

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Put your own Spoonacular API key in the environment before running:
# Windows PowerShell: $env:SPOONACULAR_API_KEY="your_key"
SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY", "")

_model = None

FRIDGE_ITEMS = [
    "apple","banana","orange","lemon","lime","grape","strawberry","blueberry","raspberry",
    "watermelon","peach","pear","pineapple","mango","avocado","kiwi","tomato","cucumber",
    "carrot","broccoli","cauliflower","onion","red onion","garlic","potato","sweet potato",
    "bell pepper","jalapeno","spinach","cabbage","lettuce","celery","mushroom","zucchini",
    "eggplant","corn","milk","cheese","mozzarella","cheddar","yogurt","butter","egg",
    "heavy cream","cream cheese","chicken","beef","steak","pork","bacon","sausage","ham",
    "turkey","salmon","tuna","shrimp","bread","rice","pasta","spaghetti","tortilla","tofu",
    "flour","sugar","olive oil","ketchup","mayonnaise"
]

FRESHNESS_DB = {
    "apple":21,"banana":6,"orange":14,"lemon":21,"lime":14,"grape":10,"strawberry":4,
    "blueberry":7,"raspberry":3,"watermelon":10,"peach":5,"pear":7,"pineapple":5,
    "mango":5,"avocado":4,"kiwi":7,"tomato":7,"cucumber":7,"carrot":21,"broccoli":5,
    "cauliflower":7,"onion":30,"red onion":30,"garlic":60,"potato":30,"sweet potato":21,
    "bell pepper":7,"jalapeno":7,"spinach":5,"cabbage":14,"lettuce":7,"celery":14,
    "mushroom":7,"zucchini":7,"eggplant":7,"corn":3,"milk":10,"cheese":21,"mozzarella":7,
    "cheddar":30,"yogurt":14,"butter":30,"egg":28,"heavy cream":14,"cream cheese":14,
    "chicken":2,"beef":3,"steak":3,"pork":3,"bacon":7,"sausage":5,"ham":7,"turkey":2,
    "salmon":2,"tuna":2,"shrimp":2,"bread":7,"rice":365,"pasta":365,"spaghetti":365,
    "tortilla":14,"tofu":5,"flour":180,"sugar":730,"olive oil":365,"ketchup":180,"mayonnaise":90,
}

def get_model():
    global _model
    if _model is None:
        from ultralytics import YOLO
        _model = YOLO('yolov8s-world.pt')
        _model.set_classes(FRIDGE_ITEMS)
    return _model

def get_freshness(name):
    max_days = FRESHNESS_DB.get(name, 10)
    days = max(1, round(max_days * random.uniform(0.4, 0.8)))
    return {
        "name": name, "daysUntilSpoil": days, "maxDays": max_days,
        "urgency": "critical" if days <= 3 else "soon" if days <= 7 else "fresh"
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400
    file = request.files['image']
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
    try:
        file.save(filepath)
        model = get_model()
        results = model.predict(filepath, conf=0.1, iou=0.5)
        seen, detected = set(), []
        for r in results:
            for box in r.boxes:
                name = FRIDGE_ITEMS[int(box.cls[0])]
                if name not in seen:
                    seen.add(name)
                    detected.append(get_freshness(name))
        detected.sort(key=lambda x: x["daysUntilSpoil"])
        return jsonify({"ingredients": detected})
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

@app.route('/fetch_recipes', methods=['POST'])
def fetch_recipes():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400
    ingredients = data.get('ingredients', [])
    if not ingredients:
        return jsonify({"recipes": [], "availCuisines": [], "availDiets": []})
    if not SPOONACULAR_API_KEY:
        return jsonify({"error": "SPOONACULAR_API_KEY is not configured"}), 500

    FIND_URL = "https://api.spoonacular.com/recipes/findByIngredients"
    BULK_URL = "https://api.spoonacular.com/recipes/informationBulk"

    def spoon_find(ing_list, number=20):
        r = requests.get(FIND_URL, params={
            "ingredients": ",".join(ing_list),
            "number": number,
            "ranking": 1,
            "ignorePantry": True,
            "apiKey": SPOONACULAR_API_KEY,
        }, timeout=10)
        r.raise_for_status()
        return r.json() or []

    try:
        raw, seen_ids = [], set()

        def merge(results):
            for r in results:
                if r["id"] not in seen_ids:
                    seen_ids.add(r["id"])
                    raw.append(r)

        merge(spoon_find(ingredients))
        if not raw and len(ingredients) > 6:
            merge(spoon_find(ingredients[:6]))
        if not raw and len(ingredients) > 3:
            merge(spoon_find(ingredients[:3]))
        if not raw:
            for ing in ingredients:
                merge(spoon_find([ing], number=6))
                if len(raw) >= 12:
                    break

        if not raw:
            return jsonify({"recipes": [], "availCuisines": [], "availDiets": []})

        ids = ",".join(str(r["id"]) for r in raw)
        bulk = requests.get(
            BULK_URL, params={"ids": ids, "apiKey": SPOONACULAR_API_KEY}, timeout=10
        )
        bulk.raise_for_status()
        bulk_data = {r["id"]: r for r in bulk.json()}

        formatted, cuisine_set, diet_set = [], set(), set()
        for r in raw:
            info = bulk_data.get(r["id"], {})
            cuisines = [c.lower() for c in info.get("cuisines", [])]
            diets = [d.lower() for d in info.get("diets", [])]
            cuisine_set.update(cuisines)
            diet_set.update(diets)
            used = r.get("usedIngredientCount", 0)
            missed = r.get("missedIngredientCount", 0)
            if used == 0:
                continue
            total = used + missed
            formatted.append({
                "id": r["id"], "name": r["title"],
                "image": r.get("image", ""),
                "cookTime": info.get("readyInMinutes"),
                "cuisines": cuisines, "diets": diets,
                "url": info.get("sourceUrl", f"https://spoonacular.com/recipes/{r['id']}"),
                "used": [i["name"] for i in r.get("usedIngredients", [])],
                "missed": [i["name"] for i in r.get("missedIngredients", [])],
                "usedCount": used, "missedCount": missed,
                "matchPct": round((used / total) * 100) if total else 0,
            })

        formatted.sort(key=lambda x: (-x["matchPct"], x["missedCount"]))
        return jsonify({
            "recipes": formatted,
            "availCuisines": sorted(cuisine_set),
            "availDiets": sorted(diet_set),
        })

    except requests.exceptions.Timeout:
        return jsonify({"error": "Recipe API timed out. Please try again."}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Recipe API error: {str(e)}"}), 502
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=True)
