"""DEVELOPMENT SEED DATA — NOT FOR PRODUCTION.

Approximate per-100g nutrition values for common Arabic, Middle Eastern and
international foods, for development and testing only. All rows are marked
is_dev_seed = TRUE and confidence_level = 'estimated'. Replace with a verified
food database (e.g. USDA-derived, verified local data) before production.
"""
from __future__ import annotations

import uuid

from sqlalchemy import text

# (name, alt_names, lang, kcal, protein, carbs, fat, fiber)
DEV_FOODS = [
    # ----- Arabic / Middle Eastern -----
    ("أرز أبيض مطبوخ", ["رز", "رز أبيض", "cooked white rice"], "ar", 130, 2.7, 28.0, 0.3, 0.4),
    ("خبز عربي", ["خبز", "كماج", "pita bread"], "ar", 275, 9.0, 55.0, 1.2, 2.2),
    ("حمص (طبق)", ["حمص بطحينة", "hummus"], "ar", 166, 8.0, 14.0, 9.6, 6.0),
    ("فلافل", ["falafel", "طعمية"], "ar", 333, 13.0, 32.0, 18.0, 4.9),
    ("فول مدمس", ["فول", "ful medames"], "ar", 110, 7.6, 16.0, 2.0, 5.0),
    ("شاورما دجاج", ["شاورما", "chicken shawarma"], "ar", 215, 19.0, 6.0, 13.0, 0.5),
    ("لبنة", ["لبنه", "labneh"], "ar", 170, 8.0, 5.0, 13.0, 0.0),
    ("جبنة بيضاء", ["جبنة نابلسية", "white cheese"], "ar", 270, 17.0, 3.0, 21.0, 0.0),
    ("تبولة", ["tabbouleh"], "ar", 120, 3.0, 15.0, 6.0, 3.5),
    ("مجدرة", ["mujaddara", "عدس مع رز"], "ar", 150, 6.0, 24.0, 3.5, 4.0),
    ("منسف (مع لحم)", ["mansaf"], "ar", 190, 13.0, 14.0, 9.0, 0.6),
    ("مقلوبة", ["maqluba"], "ar", 160, 8.0, 20.0, 5.5, 1.5),
    ("كنافة", ["knafeh", "كنافة نابلسية"], "ar", 350, 7.0, 42.0, 17.0, 0.8),
    ("زيت زيتون", ["olive oil"], "ar", 884, 0.0, 0.0, 100.0, 0.0),
    ("طحينة", ["tahini"], "ar", 595, 17.0, 21.0, 54.0, 9.3),
    ("تمر", ["dates", "بلح"], "ar", 282, 2.5, 75.0, 0.4, 8.0),
    ("لبن (زبادي)", ["زبادي", "yogurt", "لبن رائب"], "ar", 61, 3.5, 4.7, 3.3, 0.0),
    ("عدس مطبوخ", ["lentils", "شوربة عدس"], "ar", 116, 9.0, 20.0, 0.4, 7.9),
    ("برغل مطبوخ", ["bulgur"], "ar", 83, 3.1, 18.6, 0.2, 4.5),
    ("كباب لحم", ["kebab"], "ar", 250, 19.0, 4.0, 17.0, 0.5),
    # ----- proteins -----
    ("صدر دجاج مشوي", ["دجاج مشوي", "grilled chicken breast", "صدور دجاج"], "ar", 165, 31.0, 0.0, 3.6, 0.0),
    ("بيض مسلوق", ["بيض", "boiled egg", "بيضة"], "ar", 155, 13.0, 1.1, 11.0, 0.0),
    ("لحم بقري مفروم قليل الدهن", ["لحمة مفرومة", "lean ground beef"], "ar", 215, 26.0, 0.0, 12.0, 0.0),
    ("سمك سلمون", ["سلمون", "salmon"], "ar", 208, 20.0, 0.0, 13.0, 0.0),
    ("تونة معلبة بالماء", ["تونة", "canned tuna"], "ar", 116, 26.0, 0.0, 1.0, 0.0),
    ("جبن قريش", ["cottage cheese"], "ar", 98, 11.0, 3.4, 4.3, 0.0),
    # ----- international -----
    ("Cooked white rice", ["rice"], "en", 130, 2.7, 28.0, 0.3, 0.4),
    ("Grilled chicken breast", ["chicken breast"], "en", 165, 31.0, 0.0, 3.6, 0.0),
    ("Oats (dry)", ["oatmeal", "شوفان"], "en", 389, 16.9, 66.3, 6.9, 10.6),
    ("Whole wheat pasta (cooked)", ["pasta"], "en", 124, 5.3, 26.5, 0.5, 3.9),
    ("Potato (boiled)", ["بطاطا مسلوقة", "potato"], "en", 87, 1.9, 20.1, 0.1, 1.8),
    ("Sweet potato (baked)", ["بطاطا حلوة"], "en", 90, 2.0, 20.7, 0.2, 3.3),
    ("Banana", ["موز"], "en", 89, 1.1, 22.8, 0.3, 2.6),
    ("Apple", ["تفاح"], "en", 52, 0.3, 13.8, 0.2, 2.4),
    ("Peanut butter", ["زبدة فول سوداني"], "en", 588, 25.0, 20.0, 50.0, 6.0),
    ("Almonds", ["لوز"], "en", 579, 21.2, 21.6, 49.9, 12.5),
    ("Milk (whole)", ["حليب كامل الدسم", "milk"], "en", 61, 3.2, 4.8, 3.3, 0.0),
    ("Greek yogurt (plain, low fat)", ["زبادي يوناني", "greek yogurt"], "en", 73, 10.0, 3.9, 1.9, 0.0),
    ("Whey protein powder", ["بروتين واي", "protein powder"], "en", 400, 80.0, 8.0, 6.0, 1.0),
    ("Avocado", ["أفوكادو"], "en", 160, 2.0, 8.5, 14.7, 6.7),
    ("Broccoli (cooked)", ["بروكلي"], "en", 35, 2.4, 7.2, 0.4, 3.3),
    ("Cucumber", ["خيار"], "en", 15, 0.7, 3.6, 0.1, 0.5),
    ("Tomato", ["بندورة", "طماطم"], "en", 18, 0.9, 3.9, 0.2, 1.2),
    ("Olive oil", ["زيت زيتون"], "en", 884, 0.0, 0.0, 100.0, 0.0),
    # ----- Hebrew entries -----
    ("אורז לבן מבושל", ["אורז"], "he", 130, 2.7, 28.0, 0.3, 0.4),
    ("חזה עוף בגריל", ["חזה עוף"], "he", 165, 31.0, 0.0, 3.6, 0.0),
    ("חומוס", ["hummus"], "he", 166, 8.0, 14.0, 9.6, 6.0),
    ("קוטג'", ["גבינת קוטג"], "he", 98, 11.0, 3.4, 4.3, 0.0),
]


def seed_foods(engine) -> int:
    import json
    inserted = 0
    with engine.begin() as conn:
        existing = conn.execute(text("SELECT count(*) FROM foods WHERE is_dev_seed")).scalar_one()
        if existing >= len(DEV_FOODS):
            return 0
        conn.execute(text("DELETE FROM foods WHERE is_dev_seed"))
        for name, alts, lang, kcal, protein, carbs, fat, fiber in DEV_FOODS:
            conn.execute(
                text("INSERT INTO foods (id, name, alternative_names, language, kcal_per_100g, "
                     "protein_per_100g, carbs_per_100g, fat_per_100g, fiber_per_100g, source, "
                     "confidence_level, is_dev_seed) VALUES (:i, :n, CAST(:a AS jsonb), :l, :k, :p, :c, :f, "
                     ":fb, 'dev_seed_not_production', 'estimated', TRUE)"),
                {"i": str(uuid.uuid4()), "n": name, "a": json.dumps(alts, ensure_ascii=False),
                 "l": lang, "k": kcal, "p": protein, "c": carbs, "f": fat, "fb": fiber},
            )
            inserted += 1
    return inserted


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
    from app.db import get_engine
    n = seed_foods(get_engine())
    print(f"Seeded {n} dev foods (marked is_dev_seed=TRUE, source=dev_seed_not_production)")
