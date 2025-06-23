import pandas as pd

# Build list of ingredients as dictionaries
data = [
    # Grains & Starches
    {"Category": "Grains & Starches", "Item": "Quick‑cook oats", "Qty used": "400 g", "Typical pack": "500 g bag"},
    {"Category": "Grains & Starches", "Item": "Granola / Müesli clusters", "Qty used": "200 g", "Typical pack": "375–500 g box"},
    {"Category": "Grains & Starches", "Item": "Instant grits / polenta", "Qty used": "150 g", "Typical pack": "250 g bag"},
    {"Category": "Grains & Starches", "Item": "Instant couscous", "Qty used": "250 g", "Typical pack": "500 g bag"},
    {"Category": "Grains & Starches", "Item": "Pasta (thin spaghetti or elbows)", "Qty used": "250 g", "Typical pack": "500 g bag"},
    {"Category": "Grains & Starches", "Item": "Instant rice", "Qty used": "150 g", "Typical pack": "250 g box"},
    {"Category": "Grains & Starches", "Item": "Quinoa (pre‑rinsed)", "Qty used": "150 g", "Typical pack": "250 g pack"},
    {"Category": "Grains & Starches", "Item": "Ramen / instant noodle cakes", "Qty used": "2 cakes (≈180 g)", "Typical pack": "multipack (3–5)"},
    {"Category": "Grains & Starches", "Item": "Instant mashed‑potato flakes", "Qty used": "120 g", "Typical pack": "250 g box"},
    {"Category": "Grains & Starches", "Item": "Wheat tortillas (25 cm)", "Qty used": "6–8 pcs ≈ 360 g", "Typical pack": "family pack"},
    {"Category": "Grains & Starches", "Item": "Crackers / crispbread", "Qty used": "150 g", "Typical pack": "200 g sleeve"},
    {"Category": "Grains & Starches", "Item": "Tortilla chips", "Qty used": "60 g", "Typical pack": "150 g bag"},

    # Legumes & Plant Protein
    {"Category": "Legumes & Plant Protein", "Item": "Red lentils", "Qty used": "200 g", "Typical pack": "500 g bag"},
    {"Category": "Legumes & Plant Protein", "Item": "Refried‑bean flakes", "Qty used": "150 g", "Typical pack": "200 g pouch"},
    {"Category": "Legumes & Plant Protein", "Item": "Hummus powder", "Qty used": "90 g", "Typical pack": "100 g pouch"},
    {"Category": "Legumes & Plant Protein", "Item": "Dried / roasted chickpeas", "Qty used": "60 g", "Typical pack": "100 g pouch"},
    {"Category": "Legumes & Plant Protein", "Item": "TVP / soy mince (optional)", "Qty used": "30 g", "Typical pack": "100 g pouch"},

    # Fats, Nuts, Seeds
    {"Category": "Fats, Nuts & Seeds", "Item": "Peanut butter (tube/jar)", "Qty used": "300 g", "Typical pack": "350–400 g"},
    {"Category": "Fats, Nuts & Seeds", "Item": "Mixed trail nuts", "Qty used": "350 g", "Typical pack": "500 g bag"},
    {"Category": "Fats, Nuts & Seeds", "Item": "Almonds", "Qty used": "80 g", "Typical pack": "100 g bag"},
    {"Category": "Fats, Nuts & Seeds", "Item": "Walnuts", "Qty used": "40 g", "Typical pack": "100 g bag"},
    {"Category": "Fats, Nuts & Seeds", "Item": "Pumpkin / sunflower seeds", "Qty used": "100 g", "Typical pack": "200 g bag"},
    {"Category": "Fats, Nuts & Seeds", "Item": "Olive oil", "Qty used": "100 ml", "Typical pack": "2 × 50 ml bottles"},

    # Fruit & Sweet Bits
    {"Category": "Fruit & Sweet Bits", "Item": "Raisins", "Qty used": "120 g", "Typical pack": "250 g bag"},
    {"Category": "Fruit & Sweet Bits", "Item": "Dried apricots", "Qty used": "70 g", "Typical pack": "200 g bag"},
    {"Category": "Fruit & Sweet Bits", "Item": "Dried pineapple / mango mix", "Qty used": "70 g", "Typical pack": "150 g bag"},
    {"Category": "Fruit & Sweet Bits", "Item": "Shredded coconut", "Qty used": "30 g", "Typical pack": "100 g sachet"},
    {"Category": "Fruit & Sweet Bits", "Item": "Dates (pitted)", "Qty used": "40 g", "Typical pack": "200 g box"},
    {"Category": "Fruit & Sweet Bits", "Item": "Banana chips", "Qty used": "40 g", "Typical pack": "150 g bag"},
    {"Category": "Fruit & Sweet Bits", "Item": "Chocolate pieces / M&Ms", "Qty used": "40 g", "Typical pack": "100 g bag"},

    # Vegetables & Savoury Adds
    {"Category": "Veg & Savoury Adds", "Item": "Mixed dehydrated vegetables", "Qty used": "120 g", "Typical pack": "150 g pouch"},
    {"Category": "Veg & Savoury Adds", "Item": "Sundried tomatoes", "Qty used": "40 g", "Typical pack": "75 g bag"},
    {"Category": "Veg & Savoury Adds", "Item": "Dried mushrooms / seaweed", "Qty used": "20 g", "Typical pack": "30 g bag"},
    {"Category": "Veg & Savoury Adds", "Item": "Tomato‑paste tube", "Qty used": "70 g", "Typical pack": "1 tube"},
    {"Category": "Veg & Savoury Adds", "Item": "Coconut‑milk powder", "Qty used": "40 g", "Typical pack": "50 g sachet"},
    {"Category": "Veg & Savoury Adds", "Item": "Vegetable bouillon cubes", "Qty used": "2 cubes", "Typical pack": "box of 8"},

    # Cheese & Dairy
    {"Category": "Cheese & Dairy", "Item": "Hard cheese block", "Qty used": "200 g", "Typical pack": "200 g"},
    {"Category": "Cheese & Dairy", "Item": "Grated Parmesan / cheese powder", "Qty used": "60 g", "Typical pack": "80 g sachet"},
    {"Category": "Cheese & Dairy", "Item": "Whole‑milk powder", "Qty used": "200 g", "Typical pack": "400 g tin"},

    # Spice / Flavour Kit
    {"Category": "Spice & Flavour Kit", "Item": "Salt & black pepper", "Qty used": "–", "Typical pack": "mini shakers"},
    {"Category": "Spice & Flavour Kit", "Item": "Cinnamon", "Qty used": "1 Tbsp", "Typical pack": "small vial"},
    {"Category": "Spice & Flavour Kit", "Item": "Italian herb mix", "Qty used": "1 tsp", "Typical pack": "small vial"},
    {"Category": "Spice & Flavour Kit", "Item": "Curry powder", "Qty used": "2 tsp", "Typical pack": "small vial"},
    {"Category": "Spice & Flavour Kit", "Item": "Taco seasoning / chili", "Qty used": "2 tsp", "Typical pack": "small vial"},
    {"Category": "Spice & Flavour Kit", "Item": "Garlic & onion powder", "Qty used": "3 tsp", "Typical pack": "small vials"},
    {"Category": "Spice & Flavour Kit", "Item": "Cumin, coriander, turmeric, ginger", "Qty used": "½ tsp each", "Typical pack": "small vials"},
    {"Category": "Spice & Flavour Kit", "Item": "Chili flakes", "Qty used": "pinch", "Typical pack": "small vial"},
    {"Category": "Spice & Flavour Kit", "Item": "Instant miso soup sachets", "Qty used": "2", "Typical pack": "sachet pack"},
    {"Category": "Spice & Flavour Kit", "Item": "Soy & hot‑sauce mini packets", "Qty used": "4–5", "Typical pack": "assorted"},

    # Fresh (Days 1‑3)
    {"Category": "Fresh Produce (eat D1‑3)", "Item": "Apples (small)", "Qty used": "2", "Typical pack": "loose"},
    {"Category": "Fresh Produce (eat D1‑3)", "Item": "Avocado (firm)", "Qty used": "1 med", "Typical pack": "loose"},
    {"Category": "Fresh Produce (eat D1‑3)", "Item": "Carrot", "Qty used": "1", "Typical pack": "loose"},
    {"Category": "Fresh Produce (eat D1‑3)", "Item": "Bell pepper or cucumber", "Qty used": "1", "Typical pack": "loose"},
    {"Category": "Fresh Produce (eat D1‑3)", "Item": "Onion (small)", "Qty used": "1", "Typical pack": "loose"},
    {"Category": "Fresh Produce (eat D1‑3)", "Item": "Garlic cloves", "Qty used": "3", "Typical pack": "loose/bulb"},
    {"Category": "Fresh Produce (eat D1‑3)", "Item": "Lemon or lime", "Qty used": "1", "Typical pack": "loose"},

    # Ready Snacks / Beverages
    {"Category": "Ready Snacks & Drinks", "Item": "Energy bars", "Qty used": "6", "Typical pack": "singles / multipack"},
    {"Category": "Ready Snacks & Drinks", "Item": "Coffee sachets / tea bags", "Qty used": "8–10 cups", "Typical pack": "box"},
    {"Category": "Ready Snacks & Drinks", "Item": "Electrolyte tabs / drink mix", "Qty used": "4–6", "Typical pack": "tube / sachets"},

    # Packaging & Fuel
    {"Category": "Packaging & Fuel", "Item": "Zip‑lock bags", "Qty used": "20–25 pcs", "Typical pack": "box"},
    {"Category": "Packaging & Fuel", "Item": "Mini screw‑top bottles", "Qty used": "1–2", "Typical pack": "outdoor shop"},
    {"Category": "Packaging & Fuel", "Item": "Pot cozy / thick stuff sack", "Qty used": "1", "Typical pack": "DIY / gear"},
    {"Category": "Packaging & Fuel", "Item": "Gas canister (≈75 min burn)", "Qty used": "1 × 230 g", "Typical pack": "outdoor shop"},
]

df = pd.DataFrame(data)

# Write to Excel file
file_path = "/Users/robing/Desktop/8_day_trail_food_checklist.xlsx"
df.to_excel(file_path, index=False)

file_path
