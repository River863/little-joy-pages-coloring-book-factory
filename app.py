from pathlib import Path
import io
import zipfile
import streamlit as st
from PIL import Image, ImageOps
from factory.kdp import estimated_interior_pages
from factory.exporter import (
    slugify, build_paperback_interior, build_paperback_cover,
    build_fixed_layout_epub, build_listing_text, make_zip,
)

st.set_page_config(page_title="Little Joy Pages Factory", page_icon="🎨", layout="wide")
st.title("🎨 Little Joy Pages Coloring Book Factory")
st.caption("Upload full-book collages → split into individual pages → Kindle + paperback KDP package")

with st.sidebar:
    st.header("Little Joy Pages")
    publisher = st.text_input("Publisher / imprint", "Little Joy Pages")
    st.success("Free collage-to-book mode is active. No API key is required.")
    st.caption("Generate clean page-grid collages in ChatGPT, upload them here, and the Factory separates the panels into book pages.")

st.header("1 · Book details")
a, b = st.columns(2)
with a:
    title = st.text_input("Title", "Cute Hedgehogs")
    subtitle = st.text_input("Subtitle", "A Cozy Coloring Book")
    description = st.text_area("KDP description", "A cozy collection of adorable hedgehogs enjoying sweet everyday adventures. Relax, color, and enjoy cute scenes from Little Joy Pages.", height=150)
with b:
    trim = st.selectbox("Paperback trim", ["8.5 × 11 in", "8 × 10 in", "8.25 × 8.25 in"])
    blank_backs = st.checkbox("Blank back after each paperback coloring page", True)
    paperback = st.checkbox("Build paperback files", True)
    kindle = st.checkbox("Build Kindle files", True)
    keywords_raw = st.text_area("7 keyword phrases — one per line", "cute hedgehog coloring book\ncozy animal coloring book\nhedgehog coloring pages\nwoodland animal coloring book\ncute coloring book\nrelaxing animal coloring\nlittle joy pages", height=170)

st.header("2 · Upload full-book collage(s)")
st.caption("Best results: each collage must be ONLY coloring-page panels in a perfectly even grid. Do not include the color cover, labels, titles, gutters of different sizes, or decorative preview elements inside the page grid.")
collages = st.file_uploader("Coloring-page collages", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
cover = st.file_uploader("Finished COLOR front cover", type=["png", "jpg", "jpeg"], accept_multiple_files=False)

c1, c2, c3 = st.columns(3)
with c1:
    grid_rows = st.number_input("Rows per collage", min_value=1, max_value=10, value=4, step=1)
with c2:
    grid_cols = st.number_input("Columns per collage", min_value=1, max_value=10, value=5, step=1)
with c3:
    crop_margin = st.slider("Trim each panel edge (%)", min_value=0.0, max_value=8.0, value=1.0, step=0.5, help="Removes thin grid lines/gutters from each extracted panel.")


def split_collage(uploaded, rows, cols, edge_pct):
    image = Image.open(uploaded).convert("RGB")
    w, h = image.size
    pieces = []
    for r in range(rows):
        for c in range(cols):
            left = round(c * w / cols); right = round((c + 1) * w / cols)
            top = round(r * h / rows); bottom = round((r + 1) * h / rows)
            cell_w, cell_h = right - left, bottom - top
            mx = round(cell_w * edge_pct / 100); my = round(cell_h * edge_pct / 100)
            panel = image.crop((left + mx, top + my, right - mx, bottom - my))
            pieces.append(panel)
    return pieces

extracted = []
if collages:
    for collage in collages:
        extracted.extend(split_collage(collage, int(grid_rows), int(grid_cols), float(crop_margin)))
    st.write(f"**{len(extracted)} individual panels detected**")
    st.caption("Review these carefully. Each card below becomes one page in the book, in left-to-right/top-to-bottom order.")
    cols = st.columns(5)
    for i, panel in enumerate(extracted):
        with cols[i % 5]:
            st.image(panel, caption=f"Page {i+1}", use_container_width=True)
    if len(extracted) < 20:
        st.warning("This book currently has fewer than 20 coloring pages. Add another collage or change the grid settings if panels are missing.")

if cover:
    st.write("**Front cover preview**")
    st.image(cover, width=320)

st.header("3 · Export individual pages")
if extracted:
    page_zip = io.BytesIO()
    with zipfile.ZipFile(page_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, panel in enumerate(extracted, 1):
            out = io.BytesIO(); panel.save(out, "PNG", optimize=True)
            zf.writestr(f"page_{i:02d}.png", out.getvalue())
    st.download_button("🖼️ Download all split pages (ZIP)", page_zip.getvalue(), file_name=f"{slugify(title)}_individual_pages.zip", mime="application/zip", use_container_width=True)

st.header("4 · Build KDP files")
st.caption("The Factory fits each extracted panel onto its own page. Kindle has no blank reverse pages; paperback can automatically add blank backs.")

if st.button("📦 Build my KDP package", type="primary", use_container_width=True):
    if not extracted:
        st.error("Upload at least one coloring-page collage first."); st.stop()
    if not cover:
        st.error("Upload the finished color front cover first."); st.stop()

    slug = slugify(title)
    project = Path("books") / slug
    artwork = project / "artwork"
    artwork.mkdir(parents=True, exist_ok=True)
    image_paths = []
    for i, panel in enumerate(extracted, 1):
        dest = artwork / f"page_{i:02d}.png"
        panel.save(dest, "PNG", optimize=True)
        image_paths.append(dest)

    raw_cover = project / "approved_cover.png"
    Image.open(cover).convert("RGB").save(raw_cover, "PNG")
    kindle_cover = project / f"{slug}_kindle_cover.jpg"
    ImageOps.fit(Image.open(raw_cover).convert("RGB"), (1600, 2560), method=Image.Resampling.LANCZOS).save(kindle_cover, "JPEG", quality=95, dpi=(300, 300))

    keywords = [k.strip() for k in keywords_raw.splitlines() if k.strip()][:7]
    while len(keywords) < 7: keywords.append("")
    page_count = estimated_interior_pages(len(image_paths), blank_backs)

    try:
        with st.spinner("Separating panels and building Kindle + paperback files..."):
            if kindle:
                build_fixed_layout_epub(image_paths, kindle_cover, project / f"{slug}_kindle.epub", title, publisher)
            if paperback:
                build_paperback_interior(image_paths, project / f"{slug}_paperback_interior.pdf", trim, title, publisher, blank_backs)
                build_paperback_cover(raw_cover, project / f"{slug}_paperback_cover.pdf", trim, page_count, title, subtitle, publisher, description)
            instructions = build_listing_text(title, subtitle, description, keywords, trim, paperback, kindle, page_count)
            (project / "KDP_LISTING.txt").write_text(instructions, encoding="utf-8")
            make_zip(project, project / f"{slug}_complete_package.zip")
        st.session_state["built_project"] = str(project); st.session_state["built_slug"] = slug
        st.success("Done! Your separated pages and KDP publishing package are ready below.")
    except Exception as e:
        st.error(f"Package build failed: {e}")

if st.session_state.get("built_project"):
    project = Path(st.session_state["built_project"]); slug = st.session_state["built_slug"]
    st.header("5 · Download finished publishing files")
    downloads = [
        (project / f"{slug}_kindle.epub", "📱 Kindle EPUB", "application/epub+zip"),
        (project / f"{slug}_kindle_cover.jpg", "🖼️ Kindle cover JPG", "image/jpeg"),
        (project / f"{slug}_paperback_interior.pdf", "📄 Paperback interior PDF", "application/pdf"),
        (project / f"{slug}_paperback_cover.pdf", "📕 Paperback full-wrap cover PDF", "application/pdf"),
        (project / "KDP_LISTING.txt", "📋 KDP listing instructions", "text/plain"),
        (project / f"{slug}_complete_package.zip", "📦 Complete package ZIP", "application/zip"),
    ]
    for path, label, mime in downloads:
        if path.exists(): st.download_button(label, path.read_bytes(), file_name=path.name, mime=mime, use_container_width=True)

st.divider()
st.caption("Recommended production workflow: generate one or more clean, evenly spaced page-grid collages in ChatGPT → upload collage(s) → verify every extracted page → upload the separate color cover → build KDP package → preview Kindle in Kindle Previewer and paperback in KDP Print Previewer before publishing.")
