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


"""
"""
#List
"""

from openai import OpenAI
client = OpenAI()

vector_stores = client.vector_stores.list()
print(vector_stores)

"""

#Delete
"""

from openai import OpenAI
client = OpenAI()

# 1. List all vector stores
page = client.vector_stores.list()
vector_stores = page.data  # this is a list of VectorStore objects

# 2. Extract all IDs
vector_store_ids = [vs.id for vs in vector_stores]

# 3. Delete each vector store by ID
for vs_id in vector_store_ids:
    try:
        deleted = client.vector_stores.delete(vector_store_id=vs_id)
        print(f"Deleted vector store {vs_id}: {deleted}")
    except Exception as e:
        print(f"Failed to delete {vs_id}: {e}")

"""