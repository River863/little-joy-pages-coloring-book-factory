import base64
import json
import os
import re
from pathlib import Path
from openai import OpenAI
from .prompts import page_prompt, scene_planner_prompt

TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-5.6")
IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1.5")


def client() -> OpenAI:
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def _parse_numbered(text: str, expected: int) -> list[str]:
    lines = []
    for raw in text.splitlines():
        item = re.sub(r"^\s*\d+[.)-]?\s*", "", raw).strip()
        if item and item != raw.strip() or re.match(r"^\s*\d+", raw):
            if item:
                lines.append(item)
    if len(lines) < expected:
        lines = [x.strip(" -•\t") for x in text.splitlines() if x.strip()][:expected]
    return lines[:expected]


def plan_scenes(concept: str, pages: int, audience: str, special_scenes: str, sayings: bool) -> list[str]:
    prompt = scene_planner_prompt(concept, pages, audience, special_scenes, sayings)
    response = client().responses.create(model=TEXT_MODEL, input=prompt)
    scenes = _parse_numbered(response.output_text, pages)
    if len(scenes) != pages:
        raise RuntimeError(f"Planner returned {len(scenes)} scenes; expected {pages}.")
    return scenes


def generate_page(scene: str, output_path: Path, extra_style: str = "", quality: str = "high") -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = client().images.generate(
        model=IMAGE_MODEL,
        prompt=page_prompt(scene, extra_style),
        size="1024x1536",
        quality=quality,
        background="opaque",
        n=1,
    )
    image_b64 = result.data[0].b64_json
    output_path.write_bytes(base64.b64decode(image_b64))
    return output_path


def save_project(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_project(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
