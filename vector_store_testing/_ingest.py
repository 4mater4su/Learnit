import os
from openai import OpenAI

client = OpenAI()

# 1️⃣ Create—or retrieve—a vector store
VS_NAME = "Experiment_VS"

# Try to find an existing store with that name
stores = client.vector_stores.list().data
vs = next((s for s in stores if s.name == VS_NAME), None)

if vs is None:
    print(f"❓ No existing vector store named {VS_NAME!r}, creating new one…")
    vs = client.vector_stores.create(name=VS_NAME)
else:
    print(f"✔ Reusing existing vector store {VS_NAME!r}: {vs.id}")

print("Vector store ID:", vs.id, "\n")

# Persist the VS ID for later (e.g. in a .env or config file)
with open(".vector_store_id", "w") as f:
    f.write(vs.id)

# 2️⃣ Upload & attach each file
for i in range(1, 6):
    path = f"pages/page_{i}.pdf"
    print(f"Uploading {path!r}…")
    with open(path, "rb") as f:
        file_obj = client.files.create(
            file=f,
            purpose="user_data"
        )
    print(" → File ID:", file_obj.id)

    print(" Attaching to vector store…")
    vsf = client.vector_stores.files.create(
        vector_store_id=vs.id,
        file_id=file_obj.id,
        attributes={"page": str(i)}
    )
    print(" → Attached as:", vsf.id, "\n")

print("✅ Ingestion complete. You can now query this store anytime.")