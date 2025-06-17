import os
import platform
import subprocess
from openai import OpenAI

client = OpenAI()

# ——————————————————————————————
# 1️⃣ Load your existing vector store ID
try:
    with open(".vector_store_id", "r") as f:
        vs_id = f.read().strip()
except FileNotFoundError:
    raise RuntimeError("Missing .vector_store_id — run ingest_pages.py first!")

# ——————————————————————————————
# 2️⃣ Run your query
user_query = "Wie sieht die Diagnostik bei einer Schenkelhalsfraktur aus?"
response = client.responses.create(
    model="gpt-4o-mini",
    input=user_query,
    tools=[{
        "type": "file_search",
        "vector_store_ids": [vs_id]
    }]
)

# ——————————————————————————————
# 3️⃣ Extract all cited files
cited = []
for msg in response.output:
    if getattr(msg, "type", None) == "message":
        for part in msg.content:
            for ann in getattr(part, "annotations", []):
                if getattr(ann, "type", "") == "file_citation":
                    cited.append((ann.filename, ann.file_id))

if not cited:
    print("⚠ No files were cited in the response.")
    exit(0)

print("🔖 Cited files:")
for filename, file_id in cited:
    print(f"- {filename}: {file_id}")
print("\n\n")
# ——————————————————————————————
# 4️⃣ Download & open the *first* cited file
first_filename, first_file_id = cited[0]

print(first_filename)

