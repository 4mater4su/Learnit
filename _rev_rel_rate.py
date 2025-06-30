"""

__rev_rel_rate.py

"""

import re
from pydantic import BaseModel
from typing import List, Tuple, Set, Dict
from openai import OpenAI
import json
import os

STATS_DIR = "relation_stats"

def sanitize_name(name: str) -> str:
    """Keep letters, numbers, dash/underscore. Replace spaces and other chars with underscores."""
    sanitized = re.sub(r'[^A-Za-z0-9_\-]', '_', name.replace(' ', '_'))
    return sanitized[:100]

# ------------------------------------------
# OpenAI-Client initialisieren
# ------------------------------------------
client = OpenAI()

# ------------------------------------------
# Datenklassen
# ------------------------------------------
class QAPair(BaseModel):
    question: str
    answer: str

class QAPairs(BaseModel):
    qa_pairs: List[QAPair]

class Relation(BaseModel):
    subject: str
    predicate: str
    object: str

class QuestionRelations(BaseModel):
    question: str
    relations: List[Relation]

class QARelationsList(BaseModel):
    question_relations: List[QuestionRelations]

class RelationStat(BaseModel):
    subject: str
    predicate: str
    object: str
    repetition_count: int = 0
    average_difficulty: float = 0.0

# ------------------------------------------
# LearningObjective-Klasse
# ------------------------------------------
class LearningObjective(BaseModel):
    title: str
    relations: List[Tuple[str, str, str]]

    qa_pairs: List[QAPair] = []
    qa_relations: List[QuestionRelations] = []
    stats: Dict[Tuple[str, str, str], RelationStat] = {}

    @property
    def stats_file(self):
        sanitized = sanitize_name(self.title)
        return os.path.join(STATS_DIR, f"relation_stats_{sanitized}.json")

    # --- Stats laden & speichern ---
    def load_stats(self):
        os.makedirs(STATS_DIR, exist_ok=True)
        if os.path.exists(self.stats_file):
            with open(self.stats_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.stats = {
                (item["subject"], item["predicate"], item["object"]): RelationStat(**item)
                for item in data
            }
        else:
            self.stats = {
                r: RelationStat(subject=r[0], predicate=r[1], object=r[2])
                for r in self.relations
            }

    def save_stats(self):
        os.makedirs(STATS_DIR, exist_ok=True)
        data = [stat.model_dump() for stat in self.stats.values()]
        with open(self.stats_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # --- Q&A generieren ---
    def generate_qa(self, client):
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
                        f"{json.dumps(self.relations, ensure_ascii=False)}\n\n"
                        "Generiere für jede unterschiedliche Prädikat-Gruppe eine "
                        "sinnvolle Frage und antworte kurz mit den jeweiligen Objekten."
                    )
                }
            ],
            response_format=QAPairs
        )
        self.qa_pairs = completion.choices[0].message.parsed.qa_pairs

    # --- Mapping von Fragen zu Relationen generieren ---
    def generate_qa_mapping(self, client):
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
                        f"{json.dumps(self.relations, ensure_ascii=False)}\n\n"
                        "Frage-Antwort-Paare:\n"
                        f"{json.dumps([qa.model_dump() for qa in self.qa_pairs], ensure_ascii=False)}\n\n"
                        "Gib eine Liste von Objekten zurück, jedes mit den Feldern "
                        "`question` und `relations` (Liste der Tripel mit subject, predicate, object)."
                    )
                }
            ],
            response_format=QARelationsList
        )
        self.qa_relations = completion.choices[0].message.parsed.question_relations

    # --- Validierung der Relationen ---
    def validate(self) -> bool:
        orig_set: Set[Tuple[str, str, str]] = set(self.relations)
        mapped_set: Set[Tuple[str, str, str]] = {
            (r.subject, r.predicate, r.object)
            for entry in self.qa_relations
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

    # --- Frage bewerten und Stats aktualisieren ---
    def rate_question(self, question: str, rating: float):
        entry = next(e for e in self.qa_relations if e.question == question)
        for rel in entry.relations:
            key = (rel.subject, rel.predicate, rel.object)
            stat = self.stats[key]
            old_count = stat.repetition_count
            stat.repetition_count += 1
            stat.average_difficulty = (
                stat.average_difficulty * old_count + rating
            ) / stat.repetition_count
        self.save_stats()

    # --- CLI-Rating-Loop (optional, kann ausgelagert werden) ---
    def cli_rating_loop(self):
        while True:
            print("\nFragen:")
            for idx, entry in enumerate(self.qa_relations, start=1):
                print(f"{idx}. {entry.question}")
            choice = input("Wähle die Frage-Nummer zum Bewerten (oder 'q' zum Beenden): ").strip()
            if choice.lower() == "q":
                break
            if not choice.isdigit() or not (1 <= int(choice) <= len(self.qa_relations)):
                print("Ungültige Auswahl, bitte erneut versuchen.")
                continue

            idx = int(choice) - 1
            question = self.qa_relations[idx].question
            rating_str = input("Gib eine Schwierigkeit 1–5 ein: ").strip()
            try:
                rating = float(rating_str)
                if not (1.0 <= rating <= 5.0):
                    raise ValueError
            except ValueError:
                print("Ungültige Bewertung, bitte eine Zahl zwischen 1 und 5 eingeben.")
                continue

            self.rate_question(question, rating)
            print(f"Bewertung gespeichert für: «{question}»")

            print("Aktuelle Statistiken der betroffenen Relationen:")
            for rel in self.qa_relations[idx].relations:
                key = (rel.subject, rel.predicate, rel.object)
                stat = self.stats[key]
                print(f" - {key}: count={stat.repetition_count}, avg_diff={stat.average_difficulty:.2f}")

        print("Rating beendet, alle Daten gespeichert.")

    # --- Alles auf einmal: Initialisierung & Ablauf ---
    def run_all(self, client):
        print("\n=== Lernziel ===\n", self.title, "\n")
        print("--- Q&A-Paare werden generiert ---")
        self.generate_qa(client)
        for qa in self.qa_pairs:
            print(f"- {qa.question}\n  → {qa.answer}\n")
        print("--- Mapping zu Relationen wird erzeugt ---")
        self.generate_qa_mapping(client)
        for entry in self.qa_relations:
            print(f"Frage: {entry.question}")
            for r in entry.relations:
                print(f"  - ({r.subject}, {r.predicate}, {r.object})")
            print()
        print("--- Validierung ---")
        valid = self.validate()
        print("Validation erfolgreich:", valid)
        print("--- Stats laden ---")
        self.load_stats()
        print("--- CLI-Rating starten ---")
        self.cli_rating_loop()


# ------------------------------------------
# Beispielhafte Ausgangsdaten
# ------------------------------------------
lernziel = "Die einzelnen Muskelköpfe des M. quadriceps femoris, dessen Ansatz, sowie die zugehörige nervale Versorgung und deren Segmentzuordnung benennen und erläutern"

# relations: List[Tuple[str, str, str]] = [
#     ("M_quadriceps_femoris", "hat_Muskelkopf", "M_rectus_femoris"),
#     ("M_quadriceps_femoris", "hat_Muskelkopf", "M_vastus_medialis"),
#     ("M_quadriceps_femoris", "hat_Muskelkopf", "M_vastus_intermedius"),
#     ("M_quadriceps_femoris", "hat_Muskelkopf", "M_vastus_lateralis"),
#     ("M_quadriceps_femoris", "Ansatz", "Tuberositas_tibiae"),
#     ("M_quadriceps_femoris", "Innervation", "N_femoralis"),
#     ("M_quadriceps_femoris", "Innervation_Segmente", "L2-L4"),
# ]

relations: List[Tuple[str, str, str]] = [
    ("Schritte_endogene_Calcitriolsynthese", "umfasst", "Schritt_1"),
    ("Schritt_1", "enthält_Prozess", "UV-katalysierte Ringspaltung in der Haut"),
    ("Schritt_1", "tritt_auf_in", "Stratum spinosum der Epidermis"),
    ("Schritt_1", "benötigt_Substrat", "7-Dehydrocholesterin"),
    ("Schritt_1", "benötigt_Katalysator", "UV-Licht"),
    ("Schritt_1", "führt_zu", "Cholecalciferol (Vitamin D₃)"),
    ("Schritte_endogene_Calcitriolsynthese", "umfasst", "Schritt_2"),
    ("Schritt_2", "enthält_Prozess", "Hydroxylierung in der Leber"),
    ("Schritt_2", "benötigt_Substrat", "Cholecalciferol"),
    ("Schritt_2", "bei_Position", "25"),
    ("Schritt_2", "führt_zu", "25-Hydroxycholecalciferol (Calcidiol)"),
    ("Schritt_2", "hat_Funktion", "Speicherform"),
    ("Schritt_2", "hat_Funktion", "Biomarker zur Beurteilung der Vitamin-D-Versorgung"),
    ("Schritt_2", "Ergänzung", "Auch aus Nahrung aufgenommenes Vitamin D₃ wird zu Calcidiol umgewandelt"),
    ("Schritte_endogene_Calcitriolsynthese", "umfasst", "Schritt_3"),
    ("Schritt_3", "enthält_Prozess", "Hydroxylierung in der Niere"),
    ("Schritt_3", "benötigt_Substrat", "Calcidiol"),
    ("Schritt_3", "Resorption_Ort", "Primärharn"),
    ("Schritt_3", "Resorption_Rezeptor", "Megalin-Rezeptoren im proximalen Tubulus"),
    ("Schritt_3", "benötigt_Enzym", "1α-Hydroxylase"),
    ("Schritt_3", "bei_Position", "1"),
    ("Schritt_3", "führt_zu", "1,25-Dihydroxycholecalciferol (Calcitriol, aktives Vitamin D₃)"),
    ("Regulation_Calcitriolsynthese", "basiert_auf", "PTH_Parathormon"),
    ("PTH_Parathormon", "bewirkt", "Aktivierung der 1α-Hydroxylase in der Niere"),
    ("PTH_Parathormon", "Mechanismus", "cAMP-Signalweg"),
    ("PTH_Parathormon", "Rezeptor", "PTH-Rezeptor an der Zielzelle"),
    ("Regulation_Calcitriolsynthese", "basiert_auf", "Ca_HPO4_Konzentrationen"),
    ("Ca_HPO4_Konzentrationen", "Typ", "Feedback-Inhibition"),
    ("Ca_HPO4_Konzentrationen", "Effekt", "Hemmung der Aktivität der 1α-Hydroxylase"),
    ("Ca_HPO4_Konzentrationen", "Sensor", "Calciumsensor in der Zelle"),
    ("Regulation_Calcitriolsynthese", "basiert_auf", "Megalin_Rezeptor"),
    ("Megalin_Rezeptor", "Funktion", "Luminäre Internalisation von Calcidiol"),
    ("Megalin_Rezeptor", "Mechanismus", "Bindung des Calcidiol-DBP-Komplexes an den Megalin-Rezeptor"),
    ("Notwendigkeit_alimentären_Vitamin_D_Zufuhr", "Beeinflussende_Faktoren", "Syntheserate"),
    ("Syntheserate", "Faktoren", "Sonneneinstrahlung"),
    ("Syntheserate", "Faktoren", "Hautfarbe"),
    ("Syntheserate", "Effekt", "Melanin hemmt photochemische Aktivierung"),
    ("Notwendigkeit_alimentären_Vitamin_D_Zufuhr", "Beeinflussende_Faktoren", "Beitrag"),
    ("Beitrag", "Effekt", "Bei ausreichender Sonneneinstrahlung werden ca. 80–90% des Bedarfs endogen gedeckt"),
    ("Notwendigkeit_alimentären_Vitamin_D_Zufuhr", "Gründe_alimentäre_Substitution", "Unzureichende Sonneneinstrahlung in bestimmten geografischen Breiten"),
    ("Notwendigkeit_alimentären_Vitamin_D_Zufuhr", "Gründe_alimentäre_Substitution", "Geringe Sonnenexposition durch Kleidung oder Aufenthaltsdauer"),
    ("Notwendigkeit_alimentären_Vitamin_D_Zufuhr", "Gründe_alimentäre_Substitution", "Dunklere Hautfarbe"),
    ("Notwendigkeit_alimentären_Vitamin_D_Zufuhr", "Gründe_alimentäre_Substitution", "Höheres Lebensalter"),
    ("Notwendigkeit_alimentären_Vitamin_D_Zufuhr", "Gründe_alimentäre_Substitution", "Enzymdefekte"),
    ("Notwendigkeit_alimentären_Vitamin_D_Zufuhr", "Gründe_alimentäre_Substitution", "Bedeutung der Zufuhr über Nahrung oder Supplemente"),
]

# ------------------------------------------
# Main: Ausführen als Standalone-Programm
# ------------------------------------------
if __name__ == "__main__":
    lo = LearningObjective(
        title=lernziel,
        relations=relations,
    )
    lo.run_all(client)
