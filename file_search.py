from openai import OpenAI
client = OpenAI()

VECTOR_STORE_ID = "vs_6850312a8e008191a03c08c53f44f506"


# Create vector store
vector_store = client.vector_stores.create(
    name="Support FAQ",
)

# Upload file
client.vector_stores.files.upload_and_poll(
    vector_store_id=vector_store.id,
    file=open("/Users/robing/Desktop/projects/Learnit/PDFs/M10_komplett_S1-6.pdf", "rb")
)

# RAG
response = client.responses.create(
    model="gpt-4o-mini",
    input="Sichere Frakturzeichen?",
    tools=[{
        "type": "file_search",
        "vector_store_ids": [VECTOR_STORE_ID]
    }]
)

raw_text = response.output[-1].content[0].text

def format_tool_response(text: str) -> str:
    sections = [sec.strip() for sec in text.split("\n\n") if sec.strip()]
    md_parts = []
    for sec in sections:
        lines = sec.splitlines()
        heading = lines[0].rstrip(':')
        items = [line.lstrip('0123456789. ').strip() for line in lines[1:]]
        md_parts.append(f"### {heading}\n")
        for item in items:
            md_parts.append(f"- {item}")
        md_parts.append("")  # blank line between sections
    return "\n".join(md_parts)

print(format_tool_response(raw_text))




