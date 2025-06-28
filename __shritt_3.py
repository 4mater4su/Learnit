from pydantic import BaseModel
from typing import List, Tuple, Set
from openai import OpenAI
import json

client = OpenAI()

# ——————————————————————————————
# 1) Ausgangsdaten und Q&A-Generierung
# ——————————————————————————————

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
