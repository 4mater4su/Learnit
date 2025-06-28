from openai import OpenAI
client = OpenAI()

# One-shot example: 
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

# Dein Input-Text:
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
    messages=[
        {"role": "user", "content": prompt}
    ]
)

print(completion.choices[0].message.content)
