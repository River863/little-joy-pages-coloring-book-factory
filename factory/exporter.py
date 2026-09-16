import html
import re
import shutil
import uuid
import zipfile
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from .kdp import TRIMS, estimated_interior_pages, paperback_cover_dimensions


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "coloring-book"


def _fit_image(image_path: Path, width_pt: float, height_pt: float, margin_pt: float = 36):
    im = Image.open(image_path).convert("RGB")
    max_w, max_h = width_pt - 2 * margin_pt, height_pt - 2 * margin_pt
    ratio = min(max_w / im.width, max_h / im.height)
    draw_w, draw_h = im.width * ratio, im.height * ratio
    return im, (width_pt - draw_w) / 2, (height_pt - draw_h) / 2, draw_w, draw_h


def build_paperback_interior(image_paths: list[Path], output_pdf: Path, trim_name: str, title: str, publisher: str = "Little Joy Pages", blank_backs: bool = True):
    trim = TRIMS[trim_name]
    w, h = trim.width * 72, trim.height * 72
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output_pdf), pagesize=(w, h), pageCompression=1)
    c.setTitle(title)
    c.setAuthor(publisher)
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(w / 2, h * .58, title)
    c.setFont("Helvetica", 12)
    c.drawCentredString(w / 2, h * .52, publisher)
    c.showPage()
    c.setFont("Helvetica", 9)
    c.drawString(54, 72, f"© {publisher}. All rights reserved.")
    c.showPage()
    for path in image_paths:
        im, x, y, dw, dh = _fit_image(path, w, h, margin_pt=36)
        c.drawImage(ImageReader(im), x, y, dw, dh, preserveAspectRatio=True, mask="auto")
        c.showPage()
        if blank_backs:
            c.showPage()
    c.save()
    return output_pdf


def build_paperback_cover(cover_art: Path, output_pdf: Path, trim_name: str, page_count: int, title: str, subtitle: str, publisher: str, back_copy: str = "") -> Path:
    dims = paperback_cover_dimensions(trim_name, page_count)
    w, h = dims["width"] * 72, dims["height"] * 72
    bleed = 0.125 * 72
    trim = TRIMS[trim_name]
    back_w = trim.width * 72
    spine_w = dims["spine"] * 72
    front_x = bleed + back_w + spine_w
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output_pdf), pagesize=(w, h), pageCompression=1)
    c.setFillColorRGB(0.96, 0.86, 0.96)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    art = Image.open(cover_art).convert("RGB")
    target_w = trim.width * 72 + bleed
    target_h = trim.height * 72 + 2 * bleed
    ratio = max(target_w / art.width, target_h / art.height)
    resized = art.resize((int(art.width * ratio), int(art.height * ratio)), Image.Resampling.LANCZOS)
    left = max(0, (resized.width - int(target_w)) // 2)
    top = max(0, (resized.height - int(target_h)) // 2)
    crop = resized.crop((left, top, left + int(target_w), top + int(target_h)))
    c.drawImage(ImageReader(crop), front_x, 0, target_w, target_h, mask="auto")

    safe_front_center = front_x + (trim.width * 72) / 2
    c.setFillColorRGB(1, 1, 1)
    c.setStrokeColorRGB(0.35, 0.15, 0.35)
    c.roundRect(front_x + 36, h - 205, trim.width * 72 - 72, 135, 18, fill=1, stroke=1)
    c.setFillColorRGB(0.20, 0.08, 0.22)
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(safe_front_center, h - 125, title[:48])
    if subtitle:
        c.setFont("Helvetica", 11)
        c.drawCentredString(safe_front_center, h - 151, subtitle[:80])
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(safe_front_center, 40, publisher)

    c.setFillColorRGB(0.20, 0.08, 0.22)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(bleed + 36, h - 90, "Little Joy Pages")
    c.setFont("Helvetica", 10)
    text = c.beginText(bleed + 36, h - 120)
    text.setLeading(14)
    copy = back_copy or "A cozy collection of original coloring pages made for relaxing, creative moments."
    words, line = copy.split(), ""
    for word in words:
        candidate = (line + " " + word).strip()
        if c.stringWidth(candidate, "Helvetica", 10) > back_w - 100:
            text.textLine(line)
            line = word
        else:
            line = candidate
    if line:
        text.textLine(line)
    c.drawText(text)
    c.setFillColorRGB(1, 1, 1)
    c.rect(bleed + back_w - 180, bleed + 24, 144, 72, fill=1, stroke=0)
    c.save()
    return output_pdf


def build_kindle_cover(cover_art: Path, output_jpg: Path, title: str, publisher: str) -> Path:
    im = Image.open(cover_art).convert("RGB")
    im = ImageOps.fit(im, (1600, 2560), method=Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(im)
    draw.rounded_rectangle((100, 130, 1500, 500), radius=45, fill="white", outline="black", width=5)
    font = ImageFont.load_default(size=54)
    small = ImageFont.load_default(size=28)
    draw.text((800, 245), title, fill="black", font=font, anchor="mm")
    draw.text((800, 430), publisher, fill="black", font=small, anchor="mm")
    output_jpg.parent.mkdir(parents=True, exist_ok=True)
    im.save(output_jpg, "JPEG", quality=95, dpi=(300, 300))
    return output_jpg


def build_fixed_layout_epub(image_paths: list[Path], cover_jpg: Path, output_epub: Path, title: str, publisher: str) -> Path:
    work = output_epub.parent / "_epub_build"
    if work.exists():
        shutil.rmtree(work)
    (work / "META-INF").mkdir(parents=True)
    (work / "OEBPS" / "images").mkdir(parents=True)
    (work / "OEBPS" / "pages").mkdir(parents=True)
    (work / "mimetype").write_text("application/epub+zip", encoding="utf-8")
    (work / "META-INF" / "container.xml").write_text('<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>', encoding="utf-8")

    cover_dest = work / "OEBPS" / "images" / "cover.jpg"
    shutil.copy2(cover_jpg, cover_dest)
    all_images = [("cover", cover_dest, "image/jpeg")]
    pages = []
    for i, source in enumerate(image_paths, 1):
        dest = work / "OEBPS" / "images" / f"page_{i:02d}.jpg"
        Image.open(source).convert("RGB").save(dest, "JPEG", quality=92)
        all_images.append((f"img{i}", dest, "image/jpeg"))
        page = work / "OEBPS" / "pages" / f"page_{i:02d}.xhtml"
        page.write_text(f'''<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml"><head><title>Page {i}</title><meta name="viewport" content="width=1024,height=1536"/><style>html,body{{margin:0;padding:0;width:100%;height:100%;background:white}}img{{width:100%;height:100%;object-fit:contain}}</style></head><body><img src="../images/page_{i:02d}.jpg" alt="Coloring page {i}"/></body></html>''', encoding="utf-8")
        pages.append((f"p{i}", page))

    manifest = ['<item id="cover" href="images/cover.jpg" media-type="image/jpeg" properties="cover-image"/>']
    spine = []
    for i, _ in enumerate(image_paths, 1):
        manifest.append(f'<item id="img{i}" href="images/page_{i:02d}.jpg" media-type="image/jpeg"/>')
        manifest.append(f'<item id="p{i}" href="pages/page_{i:02d}.xhtml" media-type="application/xhtml+xml"/>')
        spine.append(f'<itemref idref="p{i}"/>')
    uid = uuid.uuid4()
    opf = f'''<?xml version="1.0" encoding="utf-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="bookid">urn:uuid:{uid}</dc:identifier><dc:title>{html.escape(title)}</dc:title><dc:creator>{html.escape(publisher)}</dc:creator><dc:language>en</dc:language><meta property="rendition:layout">pre-paginated</meta><meta property="rendition:orientation">portrait</meta><meta property="rendition:spread">none</meta></metadata><manifest>{''.join(manifest)}</manifest><spine>{''.join(spine)}</spine></package>'''
    (work / "OEBPS" / "content.opf").write_text(opf, encoding="utf-8")

    output_epub.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_epub, "w") as zf:
        zf.write(work / "mimetype", "mimetype", compress_type=zipfile.ZIP_STORED)
        for p in work.rglob("*"):
            if p.is_file() and p.name != "mimetype":
                zf.write(p, p.relative_to(work), compress_type=zipfile.ZIP_DEFLATED)
    shutil.rmtree(work)
    return output_epub


def build_listing_text(title: str, subtitle: str, description: str, keywords: list[str], trim: str, paperback: bool, kindle: bool, page_count: int) -> str:
    keys = "\n".join(f"{i+1}. {k}" for i, k in enumerate(keywords[:7]))
    outputs = ", ".join(x for x, on in [("Paperback", paperback), ("Kindle", kindle)] if on)
    return f"""LITTLE JOY PAGES — KDP LISTING\n\nTITLE\n{title}\n\nSUBTITLE\n{subtitle}\n\nDESCRIPTION\n{description}\n\nKEYWORDS\n{keys}\n\nEDITION OUTPUTS\n{outputs}\n\nPAPERBACK SETTINGS\nTrim size: {trim}\nPage count: {page_count}\nInterior: Black & white\nPaper: White\nBleed: No bleed\nCover finish: Matte (recommended)\nUpload manuscript: *_paperback_interior.pdf\nUpload cover: *_paperback_cover.pdf\n\nKINDLE SETTINGS\nUpload eBook manuscript: *_kindle.epub\nUpload marketing cover: *_kindle_cover.jpg\nPreview in Kindle Previewer before publishing.\n\nAI CONTENT\nThe artwork generated by this app uses generative AI. Answer KDP's AI-generated-content disclosure accurately during publishing.\n\nFINAL CHECK\nRun paperback files through KDP Print Previewer and the eBook through Kindle Previewer. Verify current KDP categories, pricing, royalties, and metadata choices at upload time.\n"""


def make_zip(project_dir: Path, output_zip: Path) -> Path:
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in project_dir.rglob("*"):
            if p.is_file() and p.resolve() != output_zip.resolve():
                zf.write(p, p.relative_to(project_dir))
    return output_zip
