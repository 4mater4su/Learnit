# __medical_text_to_json.py

import json
from openai import OpenAI

# Initialisiere den OpenAI-Client
gclient = OpenAI()

# JSON-Schema für validen Parser-Output
# Wir nutzen JSON Mode, um sicherzustellen, dass die Antwort immer gültiges JSON ist
def medical_text_to_json(input_text: str) -> dict:
    """
    Parst medizinischen Text zu hierarchischem JSON (nutzt GPT und garantiert gültiges JSON via JSON Mode).
    Gibt ein Python-Dict zurück.
    """
    example_input = (
        "Der M. deltoideus hat drei Anteile: Pars clavicularis, Pars acromialis und Pars spinalis."
        " Alle Anteile setzen am Tuberositas deltoidea humeri an."
        " Der M. deltoideus wird vom N. axillaris (C5-C6) innerviert."
    )
    example_output = '''
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

    # Baue Prompt mit Beispielpaaren
    prompt = (
        "Du bist ein KI-Parser für medizinische Texte. "
        "Wandle folgenden kurzen Text in eine hierarchische JSON-Struktur um, "
        "wobei Begriffe und Relationen erhalten bleiben.\n"  
        f"Beispiel:\nInput:\n{example_input}\nOutput:\n{example_output}\n\n"
        f"Input:\n{input_text.strip()}\nOutput:"
    )

    # Anfrage an GPT mit JSON Mode
    response = gclient.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )

    # Inhalt parsen und als dict zurückgeben
    return json.loads(response.choices[0].message.content)


# --- Beispielhafte Nutzung ---
if __name__ == "__main__":
    test_text = "Der M. biceps brachii hat zwei Köpfe: Caput longum und Caput breve."
    result = medical_text_to_json(test_text)
    print(json.dumps(result, ensure_ascii=False, indent=2))
