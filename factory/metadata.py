import json
from .generator import client, TEXT_MODEL


def generate_listing(concept: str, audience: str, page_count: int) -> dict:
    prompt = f"""Create commercially useful KDP metadata for an original Little Joy Pages coloring book.
Concept: {concept}
Audience: {audience}
Coloring pages: {page_count}
Return ONLY valid JSON with keys: title, subtitle, description, keywords.
keywords must be an array of exactly 7 useful search phrases. Do not mention copyrighted franchises. Do not make unverifiable claims. Description should be appealing, natural, and ready to paste into KDP."""
    response = client().responses.create(model=TEXT_MODEL, input=prompt)
    text = response.output_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    data = json.loads(text)
    if len(data.get("keywords", [])) != 7:
        raise RuntimeError("Metadata generator must return exactly 7 keywords.")
    return data
