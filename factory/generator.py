import base64
import json
import os
import re
from pathlib import Path
from openai import OpenAI
from .prompts import page_prompt, scene_planner_prompt

TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-5.6-terra")
IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2.5-sunburst")


def client() -> OpenAI:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")
    return OpenAI(api_key=key)


def _parse_numbered(text: str, expected: int) -> list[str]:
    lines = []
    for raw in text.splitlines():
        if re.match(r"^\s*\d+[.)-]?\s*", raw):
            item = re.sub(r"^\s*\d+[.)-]?\s*", "", raw).strip()
            if item:
                lines.append(item)
    if len(lines) < expected:
        lines = [x.strip(" -•\t") for x in text.splitlines() if x.strip()][:expected]
    return lines[:expected]


def plan_scenes(concept: str, pages: int, audience: str, special_scenes: str, sayings: bool) -> list[str]:
    response = client().responses.create(
        model=TEXT_MODEL,
        input=scene_planner_prompt(concept, pages, audience, special_scenes, sayings),
    )
    scenes = _parse_numbered(response.output_text, pages)
    if len(scenes) != pages:
        raise RuntimeError(f"Planner returned {len(scenes)} scenes; expected {pages}.")
    return scenes


def _write_image(prompt: str, output_path: Path, size: str, quality: str = "high") -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = client().images.generate(
        model=IMAGE_MODEL,
        prompt=prompt,
        size=size,
        quality=quality,
        background="opaque",
        n=1,
    )
    output_path.write_bytes(base64.b64decode(result.data[0].b64_json))
    return output_path


def generate_page(scene: str, output_path: Path, extra_style: str = "", quality: str = "high") -> Path:
    return _write_image(page_prompt(scene, extra_style), output_path, "1024x1536", quality)


def generate_cover_art(concept: str, output_path: Path, quality: str = "high") -> Path:
    prompt = f"""Create ONE polished, colorful, original commercial coloring-book cover illustration for this concept: {concept}.
Cute, cozy, joyful, premium children's/publishing illustration. Strong central character composition, lively background accents, professional visual hierarchy. Leave generous uncluttered space near the upper third for a title to be added later by software. Do NOT render any words, letters, logos, author names, barcodes, watermarks, borders, mockups, books, spines, or multiple panels. Portrait composition."""
    return _write_image(prompt, output_path, "1600x2560", quality)


def save_project(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_project(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
