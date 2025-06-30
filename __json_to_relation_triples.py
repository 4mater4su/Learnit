# __json_to_relation_triples.py

import json
from openai import OpenAI

client = OpenAI()

def json_to_relation_triples(json_str: str) -> list[tuple[str, str, str]]:
    """
    Wandelt hierarchisches JSON in eine Liste von Relationstripeln um.
    Verwendet GPT im JSON Mode mit JSON Schema, so dass ausschließlich ein valides JSON-Objekt
    mit einer "relations"-Liste zurückgegeben wird.
    """
    example_json = '''
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
'''.strip()
    example_relations = '''
{
  "relations": [
    ["M_deltoideus", "hat_Anteil", "Pars_clavicularis"],
    ["M_deltoideus", "hat_Anteil", "Pars_acromialis"],
    ["M_deltoideus", "hat_Anteil", "Pars_spinalis"],
    ["M_deltoideus", "Ansatz", "Tuberositas_deltoidea_humeri"],
    ["M_deltoideus", "Innervation_Nerv", "N_axillaris"],
    ["M_deltoideus", "Innervation_Segmente", "C5-C6"]
  ]
}
'''.strip()

    prompt = f"""
Du bist ein KI-Konverter für hierarchische JSON-Strukturen.
Wandle folgende JSON in ein Objekt mit einer einzigen Eigenschaft "relations",
welche eine Liste von Tripeln (Subjekt, Relation, Objekt) enthält.
Gebe ausschließlich ein valides JSON wie im Beispiel zurück:

{example_relations}

Input JSON:
{json_str.strip()}

Output:"""

    response = client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=[{"role": "user", "content": prompt}],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "relation_triples",
                "schema": {
                    "type": "object",
                    "properties": {
                        "relations": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 3,
                                "maxItems": 3
                            }
                        }
                    },
                    "required": ["relations"],
                    "additionalProperties": False
                },
                "strict": True
            }
        }
    )

    parsed = json.loads(response.choices[0].message.content)
    return [tuple(item) for item in parsed["relations"]]


if __name__ == "__main__":
    test_json = '''
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
'''.strip()
    results = json_to_relation_triples(test_json)
    for result in results:
      print(result)
