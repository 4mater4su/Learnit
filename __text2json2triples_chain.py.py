# __text2json2triples_chain.py

"""
Dieses Skript verbindet die beiden Module __medical_text_to_json.py und __json_to_relation_triples.py.
Es verarbeitet medizinischen Text, wandelt ihn in hierarchisches JSON um und extrahiert anschließend Relationstripel.
Statt CLI-Argumenten wird eine Variable input_text verwendet.
"""
import json

# Importiere Funktionen aus den Modulen
from __medical_text_to_json import medical_text_to_json
from __json_to_relation_triples import json_to_relation_triples

def process_text(input_text: str):
    """
    Verarbeitet den gegebenen Text: Erstellt hierarchisches JSON und extrahiert Relationstripel.
    """
    # Schritt 1: Text zu JSON
    structured_json = medical_text_to_json(input_text)
    print("Hierarchisches JSON:\n", json.dumps(structured_json, ensure_ascii=False, indent=2))

    # Schritt 2: JSON zu Relationstripeln
    json_str = json.dumps(structured_json, ensure_ascii=False)
    triples = json_to_relation_triples(json_str)
    print("\nRelationstripel:")
    for subj, rel, obj in triples:
        print(f"- ({subj}, {rel}, {obj})")

    return triples

# Beispielhafte Nutzung via Variable
if __name__ == "__main__":
    # Setze hier deinen medizinischen Text
    input_text = (
        """## Schritte der endogenen Calcitriolsynthese

- **Schritt 1: UV-katalysierte Ringspaltung in der Haut**
  - Im Stratum spinosum der Epidermis wird aus **7-Dehydrocholesterin** durch UV-Licht eine photolytische Aufspaltung des B-Rings katalysiert.
  - Es entsteht **Cholecalciferol (Vitamin D₃)**.

- **Schritt 2: Hydroxylierung in der Leber**
  - Cholecalciferol wird in der Leber an Position 25 hydroxyliert.
  - Es entsteht **25-Hydroxycholecalciferol (Calcidiol)**.
  - Calcidiol ist die Speicherform und kann im Blut nachgewiesen werden.
  - Auch aus der Nahrung aufgenommenes Vitamin D₃ wird zu Calcidiol umgewandelt. Daher dient Calcidiol als Biomarker zur Beurteilung der `Vitamin-D-Versorgung`.

- **Schritt 3: Hydroxylierung in der Niere**
  - Calcidiol gelangt in den Primärharn und wird dort von luminal liegenden Megalin-Rezeptoren im proximalen Tubulus resorbiert.
  - Intrazellulär wird Calcidiol durch die `1α-Hydroxylase` (in der Niere) an Position 1 hydroxyliert. 
  - Es entsteht **1,25-Dihydroxycholecalciferol (Calcitriol, aktives Vitamin D₃)**.

---

## Regulation der Calcitriolsynthese

- **PTH (Parathormon):**
  - Aktiviert die `1α-Hydroxylase` in der Niere über den cAMP-Signalweg.
  - Wird über den PTH-Rezeptor an der Zielzelle vermittelt.

- **Ca²⁺- und HPO₄²⁻-Konzentrationen (Feedback-Inhibition):**
  - Erhöhte intrazelluläre Spiegel von `Ca²⁺` und `HPO₄²⁻` hemmen die Aktivität der `1α-Hydroxylase`.
  - Die Regulation erfolgt über einen Calciumsensor in der Zelle.

- **Megalin-Rezeptor:**
  - Luminale Internalisation von Calcidiol erfolgt durch Bindung des Calcidiol-DBP-Komplexes an den Megalin-Rezeptor im proximalen Tubulus der Niere.

---

## Notwendigkeit der alimentären Vitamin-D-Zufuhr

- **Beeinflussende Faktoren der endogenen Synthese:**
  - Die Rate der endogenen Synthese hängt v.a. von der Sonneneinstrahlung und der Hautfarbe ab.
    - Melanin schützt zwar vor UV-Licht, hemmt jedoch die photochemische Aktivierung und somit die endogene Synthese.
  - Bei ausreichender Sonneneinstrahlung werden ca. 80–90% des Bedarfs endogen gedeckt.

- **Gründe für alimentäre Substitution:**
  - In bestimmten geografischen Breiten ist die Sonneneinstrahlung häufig unzureichend, um genug Vitamin D₃ zu synthetisieren.
  - Weitere Faktoren: geringe Sonnenexposition (Kleidung, Aufenthaltsdauer), dunklere Hautfarbe, höheres Lebensalter, Enzymdefekte.
  - In diesen Fällen ist die **Zufuhr über die Nahrung** (z.B. Fisch, Milchprodukte) oder Supplemente bedeutsam.
"""
    )
    process_text(input_text)
