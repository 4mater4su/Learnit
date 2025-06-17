from openai import OpenAI
import os

client = OpenAI()

# Load the ID (same as before)
with open(".vector_store_id") as f:
    vs_id = f.read().strip()

resp = client.vector_stores.delete(vector_store_id=vs_id)
print("Deleted vector store:", resp)

# If you want, also remove your local record
os.remove(".vector_store_id")
print("Removed .vector_store_id")
