from pathlib import Path
import shutil
import streamlit as st
from PIL import Image, ImageOps
from factory.kdp import estimated_interior_pages
from factory.exporter import (
    slugify, build_paperback_interior, build_paperback_cover,
    build_fixed_layout_epub, build_listing_text, make_zip,
)

st.set_page_config(page_title="Little Joy Pages Factory", page_icon="🎨", layout="wide")
st.title("🎨 Little Joy Pages Coloring Book Factory")
st.caption("No API key needed · Upload approved artwork → Kindle first → paperback package")

with st.sidebar:
    st.header("Little Joy Pages")
    publisher = st.text_input("Publisher / imprint", "Little Joy Pages")
    st.success("Free packaging mode is active. No OpenAI API key is required.")
    st.caption("Create/approve artwork in ChatGPT, then upload the individual pages here. The Factory handles KDP packaging.")

st.header("1 · Book details")
a, b = st.columns(2)
with a:
    title = st.text_input("Title", "Cute Hedgehogs")
    subtitle = st.text_input("Subtitle", "A Cozy Coloring Book")
    audience = st.selectbox("Audience", ["Kids", "Teens", "Adults", "Teens & adults", "All ages"], index=4)
    description = st.text_area("KDP description", "A cozy collection of adorable hedgehogs enjoying sweet everyday adventures. Relax, color, and enjoy 20 cute scenes from Little Joy Pages.", height=150)
with b:
    trim = st.selectbox("Paperback trim", ["8.5 × 11 in", "8 × 10 in", "8.25 × 8.25 in"])
    blank_backs = st.checkbox("Blank back after each paperback coloring page", True)
    paperback = st.checkbox("Build paperback files", True)
    kindle = st.checkbox("Build Kindle files", True)
    keywords_raw = st.text_area("7 keyword phrases — one per line", "cute hedgehog coloring book\ncozy animal coloring book\nhedgehog coloring pages\nwoodland animal coloring book\ncute coloring book\nrelaxing animal coloring\nlittle joy pages", height=170)

st.header("2 · Upload the finished artwork")
st.caption("Upload each coloring page as its own PNG or JPG. Files are sorted by filename, so names like page_01.png, page_02.png … page_20.png work best.")
pages = st.file_uploader("Coloring pages", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
cover = st.file_uploader("Finished COLOR cover (front cover only)", type=["png", "jpg", "jpeg"], accept_multiple_files=False)

if pages:
    pages = sorted(pages, key=lambda f: f.name.lower())
    st.write(f"**{len(pages)} coloring pages uploaded**")
    cols = st.columns(4)
    for i, f in enumerate(pages):
        with cols[i % 4]:
            st.image(f, caption=f"{i+1}. {f.name}", use_container_width=True)
    if len(pages) < 20:
        st.warning("You can build with fewer pages, but the Cute Hedgehogs plan is 20 unique coloring pages.")

if cover:
    st.write("**Approved cover**")
    st.image(cover, width=320)

st.header("3 · Build KDP files")
st.caption("Kindle has no blank reverse pages. Paperback automatically adds blank backs when selected.")

if st.button("📦 Build my KDP package", type="primary", use_container_width=True):
    if not pages:
        st.error("Upload at least one coloring page first.")
        st.stop()
    if not cover:
        st.error("Upload the finished color cover first.")
        st.stop()

    slug = slugify(title)
    project = Path("books") / slug
    artwork = project / "artwork"
    artwork.mkdir(parents=True, exist_ok=True)

    image_paths = []
    for i, uploaded in enumerate(pages, 1):
        suffix = Path(uploaded.name).suffix.lower()
        if suffix not in [".png", ".jpg", ".jpeg"]:
            suffix = ".png"
        dest = artwork / f"page_{i:02d}{suffix}"
        dest.write_bytes(uploaded.getvalue())
        image_paths.append(dest)

    raw_cover = project / "approved_cover.png"
    Image.open(cover).convert("RGB").save(raw_cover, "PNG")

    # KDP Kindle marketing cover: approved artwork, resized/cropped only — no duplicate title overlay.
    kindle_cover = project / f"{slug}_kindle_cover.jpg"
    ImageOps.fit(Image.open(raw_cover).convert("RGB"), (1600, 2560), method=Image.Resampling.LANCZOS).save(kindle_cover, "JPEG", quality=95, dpi=(300, 300))

    keywords = [k.strip() for k in keywords_raw.splitlines() if k.strip()][:7]
    while len(keywords) < 7:
        keywords.append("")
    page_count = estimated_interior_pages(len(image_paths), blank_backs)

    try:
        with st.spinner("Building Kindle + paperback files..."):
            if kindle:
                build_fixed_layout_epub(image_paths, kindle_cover, project / f"{slug}_kindle.epub", title, publisher)
            if paperback:
                build_paperback_interior(image_paths, project / f"{slug}_paperback_interior.pdf", trim, title, publisher, blank_backs)
                build_paperback_cover(raw_cover, project / f"{slug}_paperback_cover.pdf", trim, page_count, title, subtitle, publisher, description)
            instructions = build_listing_text(title, subtitle, description, keywords, trim, paperback, kindle, page_count)
            (project / "KDP_LISTING.txt").write_text(instructions, encoding="utf-8")
            make_zip(project, project / f"{slug}_complete_package.zip")
        st.session_state["built_project"] = str(project)
        st.session_state["built_slug"] = slug
        st.success("Done! Your KDP package is ready below.")
    except Exception as e:
        st.error(f"Package build failed: {e}")

if st.session_state.get("built_project"):
    project = Path(st.session_state["built_project"])
    slug = st.session_state["built_slug"]
    st.header("4 · Download")
    downloads = [
        (project / f"{slug}_kindle.epub", "📱 Kindle EPUB", "application/epub+zip"),
        (project / f"{slug}_kindle_cover.jpg", "🖼️ Kindle cover JPG", "image/jpeg"),
        (project / f"{slug}_paperback_interior.pdf", "📄 Paperback interior PDF", "application/pdf"),
        (project / f"{slug}_paperback_cover.pdf", "📕 Paperback full-wrap cover PDF", "application/pdf"),
        (project / "KDP_LISTING.txt", "📋 KDP listing instructions", "text/plain"),
        (project / f"{slug}_complete_package.zip", "📦 Complete package ZIP", "application/zip"),
    ]
    for path, label, mime in downloads:
        if path.exists():
            st.download_button(label, path.read_bytes(), file_name=path.name, mime=mime, use_container_width=True)

st.divider()
st.caption("Workflow: create artwork in ChatGPT → upload pages here → build Kindle → publish Kindle → use KDP 'Start your paperback' → upload the print files. Always preview both editions before publishing and disclose AI-generated artwork accurately when KDP asks.")
