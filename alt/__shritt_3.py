from pydantic import BaseModel
from typing import List, Tuple, Set, Dict
from openai import OpenAI
import json
import os

client = OpenAI()

# ——————————————————————————————
# 1) Ausgangsdaten und Q&A-Generierung
# ——————————————————————————————

lernziel = "Die einzelnen Muskelköpfe des M. quadriceps femoris, dessen Ansatz, sowie die zugehörige nervale Versorgung und deren Segmentzuordnung benennen und erläutern"

relations: List[Tuple[str, str, str]] = [
    ("M_quadriceps_femoris", "hat_Muskelkopf", "M_rectus_femoris"),
    ("M_quadriceps_femoris", "hat_Muskelkopf", "M_vastus_medialis"),
    ("M_quadriceps_femoris", "hat_Muskelkopf", "M_vastus_intermedius"),
    ("M_quadriceps_femoris", "hat_Muskelkopf", "M_vastus_lateralis"),
    ("M_quadriceps_femoris", "Ansatz", "Tuberositas_tibiae"),
    ("M_quadriceps_femoris", "Innervation", "N_femoralis"),
    ("M_quadriceps_femoris", "Innervation_Segmente", "L2-L4"),
]

class QAPair(BaseModel):
    question: str
    answer: str

class QAPairs(BaseModel):
    qa_pairs: List[QAPair]

def generate_qa() -> List[QAPair]:
    completion = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "Du bist ein Assistent, der aus einer Liste von Tripeln "
                    "(Subjekt, Prädikat, Objekt) lehrreiche Frage-Antwort-Paare generiert. "
                    "Gib ausschließlich validen JSON zurück, angelehnt an das folgende Schema."
                )
            },
            {
                "role": "user",
                "content": (
                    "Relationen:\n"
                    f"{json.dumps(relations, ensure_ascii=False)}\n\n"
                    "Generiere für jede unterschiedliche Prädikat-Gruppe eine "
                    "sinnvolle Frage und antworte kurz mit den jeweiligen Objekten."
                )
            }
        ],
        response_format=QAPairs
    )
    return completion.choices[0].message.parsed.qa_pairs


# ——————————————————————————————
# 2) Mapping als Liste von Frage+Relationen
# ——————————————————————————————

class Relation(BaseModel):
    subject: str
    predicate: str
    object: str

class QuestionRelations(BaseModel):
    question: str
    relations: List[Relation]

class QARelationsList(BaseModel):
    question_relations: List[QuestionRelations]

def generate_mapping(qa_pairs: List[QAPair]) -> List[QuestionRelations]:
    completion = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "Du bist ein Assistent, der zu jedem Frage-Antwort-Paar "
                    "die Liste der zugrunde liegenden Relationen liefert, "
                    "die in der Antwort vorkommen. Gib reines JSON zurück."
                )
            },
            {
                "role": "user",
                "content": (
                    "Relationen:\n"
                    f"{json.dumps(relations, ensure_ascii=False)}\n\n"
                    "Frage-Antwort-Paare:\n"
                    f"{json.dumps([qa.model_dump() for qa in qa_pairs], ensure_ascii=False)}\n\n"
                    "Gib eine Liste von Objekten zurück, jedes mit den Feldern "
                    "`question` und `relations` (Liste der Tripel mit subject, predicate, object)."
                )
            }
        ],
        response_format=QARelationsList
    )
    return completion.choices[0].message.parsed.question_relations


# ——————————————————————————————
# 3) Validierung der Relationen
# ——————————————————————————————

def validate_relations(
    original: List[Tuple[str, str, str]],
    mapped: List[QuestionRelations]
) -> bool:
    orig_set: Set[Tuple[str, str, str]] = set(original)
    mapped_set: Set[Tuple[str, str, str]] = {
        (r.subject, r.predicate, r.object)
        for entry in mapped
        for r in entry.relations
    }

    missing = orig_set - mapped_set
    extra   = mapped_set - orig_set

    if not missing and not extra:
        print("✅ Alle Relationen stimmen exakt überein.")
        return True

    if missing:
        print("❌ Fehlende Relationen:")
        for subj, pred, obj in missing:
            print(f"   - ({subj}, {pred}, {obj})")

    if extra:
        print("❌ Zusätzliche Relationen (nicht im Original):")
        for subj, pred, obj in extra:
            print(f"   - ({subj}, {pred}, {obj})")

    return False



# ——————————————————————————————
# 4) Spaced-Repetition–Stats persistieren
# ——————————————————————————————
STATS_FILE = "relation_stats.json"

class RelationStat(BaseModel):
    subject: str
    predicate: str
    object: str
    repetition_count: int = 0
    average_difficulty: float = 0.0

def load_stats(relations: List[Tuple[str, str, str]]) -> Dict[Tuple[str, str, str], RelationStat]:
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        stats = {
            (item["subject"], item["predicate"], item["object"]): RelationStat(**item)
            for item in data
        }
    else:
        stats = {
            r: RelationStat(subject=r[0], predicate=r[1], object=r[2])
            for r in relations
        }
    return stats

def save_stats(stats: Dict[Tuple[str, str, str], RelationStat]) -> None:
    data = [stat.model_dump() for stat in stats.values()]
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def rate_question(
    question: str,
    qa_relations: List[QuestionRelations],
    stats: Dict[Tuple[str, str, str], RelationStat],
    rating: float
) -> None:
    # Frage-Eintrag finden
    entry = next(e for e in qa_relations if e.question == question)
    for rel in entry.relations:
        key = (rel.subject, rel.predicate, rel.object)
        stat = stats[key]
        old_count = stat.repetition_count
        stat.repetition_count += 1
        stat.average_difficulty = (
            stat.average_difficulty * old_count + rating
        ) / stat.repetition_count


# ——————————————————————————————
# 5) CLI–Routine zum Raten
# ——————————————————————————————
def cli_rating_loop(qa_relations: List[QuestionRelations]):
    stats = load_stats(relations)
    while True:
        print("\nFragen:")
        for idx, entry in enumerate(qa_relations, start=1):
            print(f"{idx}. {entry.question}")
        choice = input("Wähle die Frage-Nummer zum Bewerten (oder 'q' zum Beenden): ").strip()
        if choice.lower() == "q":
            break
        if not choice.isdigit() or not (1 <= int(choice) <= len(qa_relations)):
            print("Ungültige Auswahl, bitte erneut versuchen.")
            continue

        idx = int(choice) - 1
        question = qa_relations[idx].question
        rating_str = input("Gib eine Schwierigkeit 1–5 ein: ").strip()
        try:
            rating = float(rating_str)
            if not (1.0 <= rating <= 5.0):
                raise ValueError
        except ValueError:
            print("Ungültige Bewertung, bitte eine Zahl zwischen 1 und 5 eingeben.")
            continue

        rate_question(question, qa_relations, stats, rating)
        save_stats(stats)
        print(f"Bewertung gespeichert für: «{question}»")

        # Optionally, show updated stats for this question's relations
        print("Aktuelle Statistiken der betroffenen Relationen:")
        for rel in qa_relations[idx].relations:
            key = (rel.subject, rel.predicate, rel.object)
            stat = stats[key]
            print(f" - {key}: count={stat.repetition_count}, avg_diff={stat.average_difficulty:.2f}")

    print("Rating beendet, alle Daten gespeichert.")


# ——————————————————————————————
# Main
# ——————————————————————————————
if __name__ == "__main__":
    # 1) Q&A erzeugen und ausgeben
    qa_pairs = generate_qa()
    print("=== Q&A Pairs ===")
    for qa in qa_pairs:
        print(f"- {qa.question}\n  → {qa.answer}\n")

    # 2) Mapping erzeugen und ausgeben
    qa_relations = generate_mapping(qa_pairs)
    print("=== Frage → Relationen ===")
    for entry in qa_relations:
        print(f"Frage: {entry.question}")
        for r in entry.relations:
            print(f"  - ({r.subject}, {r.predicate}, {r.object})")
        print()

    # 3) Validierung
    print("=== Validierungsergebnis ===")
    result = validate_relations(relations, qa_relations)
    print("Validation erfolgreich:", result)

    # 4) CLI für Rating
    cli_rating_loop(qa_relations)