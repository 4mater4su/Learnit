"""

__medtext_triples.py

"""

from openai import OpenAI

client = OpenAI()  # API-Key muss gesetzt sein (z.B. via Umgebungsvariable)

def parse_medical_text_to_json(input_text):
    """Parst medizinischen Text zu hierarchischem JSON (nutzt GPT)."""
    example_input = """
    Der M. deltoideus hat drei Anteile: Pars clavicularis, Pars acromialis und Pars spinalis. 
    Alle Anteile setzen am Tuberositas deltoidea humeri an. 
    Der M. deltoideus wird vom N. axillaris (C5-C6) innerviert.
    """
    example_output = """
    {
      "M_deltoideus": {
        "Anteile": ["Pars clavicularis", "Pars acromialis", "Pars spinalis"],
        "Ansatz": "Tuberositas deltoidea humeri",
        "Innervation": {
          "Nerv": "N. axillaris",
          "Segmente": "C5-C6"
        }
      }
    }
    """
    prompt = f"""\
Du bist ein KI-Parser für medizinische Texte. 
Wandle folgenden kurzen Text in eine hierarchische JSON-Struktur um, wobei Begriffe und Relationen erhalten bleiben. 
Beispiel:
Input:
{example_input.strip()}
Output:
{example_output.strip()}

Input:
{input_text.strip()}
Output:
"""
    completion = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}]
    )
    # Gib nur das JSON zurück (Textformat)
    return completion.choices[0].message.content.strip()

def json_to_relation_triples(json_str):
    """Wandelt hierarchisches JSON in Relationstriple-Liste (nutzt GPT)."""
    example_json = """
    {
      "M_deltoideus": {
        "Anteile": ["Pars clavicularis", "Pars acromialis", "Pars spinalis"],
        "Ansatz": "Tuberositas deltoidea humeri",
        "Innervation": {
          "Nerv": "N. axillaris",
          "Segmente": "C5-C6"
        }
      }
    }
    """
    example_relations = """
relations = [
    ("M_deltoideus", "hat_Anteil", "Pars_clavicularis"),
    ("M_deltoideus", "hat_Anteil", "Pars_acromialis"),
    ("M_deltoideus", "hat_Anteil", "Pars_spinalis"),
    ("M_deltoideus", "Ansatz", "Tuberositas_deltoidea_humeri"),
    ("M_deltoideus", "Innervation", "N_axillaris"),
    ("M_deltoideus", "Innervation_Segmente", "C5-C6")
]
    """
    prompt = f"""\
Wandle folgende hierarchische JSON-Struktur in **eine Python-Liste von Tripeln** \
(jedes Tripel ist ein Tupel der Form (Subjekt, Relation, Objekt)) um. Gebe ausschließlich die Liste von Tripeln zurück.

Beispiel:
Input:
{example_json.strip()}
Output:
{example_relations.strip()}

Input:
{json_str.strip()}
Output:
"""
    completion = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}]
    )
    # Gibt die Tripel-Liste (Text, Python-Syntax) zurück
    return completion.choices[0].message.content.strip()

# --- Beispiel für Nutzung ---

if __name__ == "__main__":
    input_text = """
    ## Anatomie und Lage des M. quadriceps femoris

    - Der **M. quadriceps femoris** ist eine **Muskelgruppe** mit vier Muskelköpfen und einer gemeinsamen Ansatzsehne.
    - Die vier Muskelköpfe sind:
      - **M. rectus femoris** (liegt auf dem Vastus intermedius)
        - **Ursprung:** Spina iliaca anterior inferior (kranial des Acetabulums)
        - **Ansatz:** Tuberositas tibiae (distal der Patella)
        - Übergreift als einziger Kopf das **Hüftgelenk** → Einziger Kopf des Quadriceps, der zur **Hüftflexion** führt.
      - **M. vastus medialis**
        - **Ursprung:** Linea aspera, Labium mediale (verläuft von frontal, distal des Trochanter major über die kaudale Seite des Femurs, kurz über dem Kniegelenk in der Kniekehle, windet sich nach medial)
        - **Ansatz:** Tuberositas tibiae; außerdem Ansatz am medialen und lateralen Tibiakondylus (distal der Patella)
      - **M. vastus intermedius**
        - **Ursprung:** Femurschaft (Vorderfläche)
        - **Ansatz:** Tuberositas tibiae, medialer und lateraler Tibiakondylus (distal der Patella)
      - **M. vastus lateralis**
        - **Ursprung:** Linea aspera, Labium laterale; Femur laterale, proximal (windet sich nach lateral um den Femurschaft)
        - **Ansatz:** Tuberositas tibiae, medialer und lateraler Tibiakondylus (distal der Patella)

    ---

    ## Physiologische und funktionelle Aspekte

    - Übergeordnetes Funktionsprinzip: **Knieextension**
    - **Hüftflexion** wird ausschließlich vom M. rectus femoris übernommen, da nur dieser das Hüftgelenk übergreift.
    - Alle Anteile sind an **Spielbeinbewegungen** beteiligt.
    - **Innervation:** N. femoralis (Segmente L2–4)
    """

    # Schritt 1: Text zu JSON
    json_str = parse_medical_text_to_json(input_text)
    print("===== Parsed JSON =====")
    print(json_str)
    print()

    # Schritt 2: JSON zu Tripel-Liste
    triples = json_to_relation_triples(json_str)
    print("===== Relationstriple-Liste =====")
    print(triples)
