LITTLE_JOY_STYLE = """Create ONE standalone printable coloring-book illustration, not a contact sheet and not multiple panels. High-quality cute/cozy professional coloring-book line art. Bold, smooth, clean black outlines on pure white. Premium composition with a clear focal character, appealing environment, balanced detail, and generous colorable spaces. Keep the complete scene inside safe margins. No grayscale, hatching, shadows, color, watermark, signature, page number, border text, random letters, speech bubbles, or photorealism. Avoid malformed anatomy and duplicated limbs. Maintain a consistent visual language suitable for a cohesive commercial coloring book."""


def page_prompt(scene: str, extra_style: str = "") -> str:
    return f"{LITTLE_JOY_STYLE}\n\nSCENE FOR THIS PAGE:\n{scene.strip()}\n\nADDITIONAL BOOK DIRECTION:\n{extra_style.strip()}"


def scene_planner_prompt(concept: str, pages: int, audience: str, special_scenes: str, sayings: bool) -> str:
    text_rule = "A few scenes may contain a very short, correctly spelled cute saying when compositionally useful." if sayings else "Do not include words or sayings in the artwork."
    return f"""Plan exactly {pages} distinct coloring-page scenes for a cohesive book.
Book concept: {concept}
Audience: {audience}
Must-have ideas: {special_scenes or 'None specified'}
{text_rule}

Make every scene visually different while keeping the same overall character/world. Avoid repetitive poses and backgrounds. Each item should describe one standalone full-page illustration with subject action, props, setting, and composition. Return concise numbered scenes only."""
