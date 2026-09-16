from dataclasses import dataclass

@dataclass(frozen=True)
class TrimSpec:
    width: float
    height: float

TRIMS = {
    "8.5 × 11 in": TrimSpec(8.5, 11.0),
    "8 × 10 in": TrimSpec(8.0, 10.0),
    "8.25 × 8.25 in": TrimSpec(8.25, 8.25),
}


def estimated_interior_pages(coloring_pages: int, blank_backs: bool, front_matter_pages: int = 2) -> int:
    count = front_matter_pages + coloring_pages * (2 if blank_backs else 1)
    if count % 2: count += 1
    return max(24, count)


def paperback_cover_dimensions(trim_name: str, page_count: int) -> dict:
    """KDP B&W white-paper paperback formula: spine = pages × 0.002252 inches."""
    trim = TRIMS[trim_name]; spine = page_count * 0.002252; bleed = 0.125
    return {"spine": spine, "width": bleed + trim.width + spine + trim.width + bleed, "height": bleed + trim.height + bleed}


def package_manifest(slug: str, paperback: bool, kindle: bool) -> list[str]:
    files = [f"{slug}/artwork/page_01.png ...", f"{slug}/KDP_LISTING.txt"]
    if paperback: files += [f"{slug}/{slug}_paperback_interior.pdf", f"{slug}/{slug}_paperback_cover.pdf"]
    if kindle: files += [f"{slug}/{slug}_kindle.epub", f"{slug}/{slug}_kindle_cover.jpg"]
    files.append(f"{slug}/{slug}_complete_package.zip"); return files
