from typing import List, Tuple
from pydantic import BaseModel, ValidationError
from openai import OpenAI

client = OpenAI()

Relation = Tuple[str, str, str]

class DuplicateResponse(BaseModel):
    is_duplicate: bool

def is_semantic_duplicate(rel1: Relation, rel2: Relation) -> bool:
    """
    Ask the LLM if rel1 and rel2 are semantically identical.
    Rel1 and Rel2 are each (subject, predicate, object).
    Returns True if the model answers 'yes', False if 'no'.
    """
    prompt = f"""
Are these two relations semantically identical?

Relation A: ({rel1[0]!r}, {rel1[1]!r}, {rel1[2]!r})
Relation B: ({rel2[0]!r}, {rel2[1]!r}, {rel2[2]!r})

Respond with exactly one of:
{{"is_duplicate": true}}
{{"is_duplicate": false}}
""".strip()

    resp = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[{"role": "user", "content": prompt}],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "duplicate_response",
                "schema": {
                    "type": "object",
                    "properties": {
                        "is_duplicate": {"type": "boolean"}
                    },
                    "required": ["is_duplicate"],
                    "additionalProperties": False
                },
                "strict": True
            }
        },
        temperature=0.0,
    )

    content = resp.choices[0].message.content

    try:
        # Pydantic v2 replacement for parse_raw
        parsed = DuplicateResponse.model_validate_json(content)
    except ValidationError as e:
        raise RuntimeError(f"Invalid JSON or schema mismatch: {content}") from e

    return parsed.is_duplicate

def merge_duplicate_relations(
    new_relations: List[Relation], 
    existing_relations: List[Relation]
) -> List[Relation]:
    """
    For each relation in new_relations, check against existing_relations.
    If no semantic duplicate is found, append to merged list.
    """
    merged = existing_relations.copy()
    for rel in new_relations:
        duplicate_found = False
        for ex in merged:
            if is_semantic_duplicate(rel, ex):
                duplicate_found = True
                print(f"Duplicate detected, skipping: {rel}")
                break
        if not duplicate_found:
            merged.append(rel)
            print(f"Added: {rel}")
    return merged

if __name__ == "__main__":
    # existing relations example
    existing_relations: List[Relation] = [
        ("M_quadriceps_femoris", "hat_Muskelkopf", "M_rectus_femoris"),
        ("M_quadriceps_femoris", "hat_Muskelkopf", "M_vastus_medialis"),
        ("M_quadriceps_femoris", "hat_Muskelkopf", "M_vastus_intermedius"),
        ("M_quadriceps_femoris", "hat_Muskelkopf", "M_vastus_lateralis"),
        ("M_quadriceps_femoris", "Ansatz", "Tuberositas_tibiae"),
        ("M_quadriceps_femoris", "Innervation", "N_femoralis"),
        ("M_quadriceps_femoris", "Innervation_Segmente", "L2-L4"),
    ]

    # new relations example
    new_relations: List[Relation] = [
        ("Schritte_endogene_Calcitriolsynthese", "umfasst", "Schritt_1"),
        ("M_quadriceps_femoris", "hat_Muskelkopf", "M_rectus_femoris"),  # should be flagged duplicate
        ("M_quadriceps_femoris", "Muskelkopf", "M_vastus_medialis"),     # probably not duplicate
        ("M_quadriceps_femoris", "hat_Muskelköpfe", "M_vastus_intermedius")
    ]

    merged = merge_duplicate_relations(new_relations, existing_relations)
    print(f"\nFinal merged list ({len(merged)} relations):")
    for r in merged:
        print(r)
