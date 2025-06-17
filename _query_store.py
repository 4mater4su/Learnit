import os
from openai import OpenAI

client = OpenAI()

# 1️⃣ Load the existing vector store ID
try:
    with open(".vector_store_id") as f:
        vs_id = f.read().strip()
except FileNotFoundError:
    raise RuntimeError("Could not find .vector_store_id—run ingest_pages.py first!")

# 2️⃣ Ask your question
user_query = "Sichere vs unsichere Frakturzeichen?"
response = client.responses.create(
    model="gpt-4o-mini",
    input=user_query,
    tools=[{
        "type": "file_search",
        "vector_store_ids": [vs_id]
    }]
)

# 3️⃣ Extract & print citations
cited = []
for msg in response.output:
    if getattr(msg, "type", None) == "message":
        for part in msg.content:
            for ann in getattr(part, "annotations", []):
                if ann.type == "file_citation":
                    cited.append((ann.filename, ann.file_id))

print("🔖 Cited files:")
for fn, fid in cited:
    print(f"- {fn}: {fid}")

# 4️⃣ Pretty-print the answer
for msg in response.output:
    if getattr(msg, "type", None) == "message":
        for part in msg.content:
            if getattr(part, "text", None):
                print("\n### Antwort\n")
                print(part.text)
                break
