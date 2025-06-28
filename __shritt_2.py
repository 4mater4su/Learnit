from openai import OpenAI
client = OpenAI()

# One-shot Example:
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

# JSON you want to convert:
input_json = """
{
  "M_quadriceps_femoris": {
    "Muskelköpfe": [
      "M_rectus_femoris",
      "M_vastus_medialis",
      "M_vastus_intermedius",
      "M_vastus_lateralis"
    ],
    "Ansatz": "Tuberositas tibiae",
    "Innervation": {
      "Nerv": "N. femoralis",
      "Segmente": "L2-L4"
    }
  }
}
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
{input_json.strip()}
Output:
"""

completion = client.chat.completions.create(
    model="gpt-4.1",
    messages=[{"role": "user", "content": prompt}]
)

print(completion.choices[0].message.content)
