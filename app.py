import os
from pathlib import Path
import streamlit as st
from factory.generator import plan_scenes, generate_page, generate_cover_art, save_project
from factory.metadata import generate_listing
from factory.kdp import estimated_interior_pages
from factory.exporter import (
    slugify, build_paperback_interior, build_paperback_cover,
    build_kindle_cover, build_fixed_layout_epub, build_listing_text, make_zip,
)

st.set_page_config(page_title="Little Joy Pages Factory", page_icon="🎨", layout="wide")
DEFAULT_STYLE = """High-quality printable coloring-book line art. Cute, cozy, polished character illustration. Bold, smooth, clean black outlines on a pure white background. Full-page composition with comfortable margins. Detailed but easy and satisfying to color. Consistent character proportions and visual language across the whole book. No grayscale, no shading, no color, no page numbers, no watermark, no random text, no contact sheet, no panels, no cropped subject, no photorealism."""

try:
    if "OPENAI_API_KEY" in st.secrets:
        os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
except Exception:
    pass

for key, default in {"scenes": [], "approved": {}, "images": {}, "listing": None, "built": False}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.title("🎨 Little Joy Pages Coloring Book Factory")
st.caption("Idea → individual high-quality pages → approve/regenerate → paperback + Kindle package")

with st.sidebar:
    st.header("Brand settings")
    publisher = st.text_input("Publisher / imprint", "Little Joy Pages")
    style = st.text_area("Little Joy Pages art direction", DEFAULT_STYLE, height=270)
    st.divider()
    st.caption("Uses GPT-Image-2.5 Sunburst by default. Your API key belongs in Streamlit Secrets as OPENAI_API_KEY and is never stored in this repository.")

st.header("1 · Tell the Factory what to make")
a, b = st.columns(2)
with a:
    concept = st.text_area("Book idea", "Cute koalas doing cozy everyday activities", height=110)
    pages = st.number_input("Coloring pages", 5, 100, 20)
    audience = st.selectbox("Audience", ["Kids", "Teens", "Adults", "Teens & adults", "All ages"], index=3)
    special = st.text_area("Must-have scenes", "Koala wearing a sleeping eye mask")
with b:
    sayings = st.checkbox("Occasional cute sayings", False)
    trim = st.selectbox("Paperback trim", ["8.5 × 11 in", "8 × 10 in", "8.25 × 8.25 in"])
    blank_backs = st.checkbox("Blank back after each coloring page", True)
    paperback = st.checkbox("Generate paperback", True)
    kindle = st.checkbox("Generate Kindle fixed-layout eBook", True)

if st.button("🧠 Create my scene plan", type="primary", use_container_width=True):
    if not os.environ.get("OPENAI_API_KEY"):
        st.error("Add OPENAI_API_KEY to Streamlit Secrets first.")
    else:
        try:
            with st.spinner("Designing distinct pages..."):
                st.session_state.scenes = plan_scenes(concept, int(pages), audience, special, sayings)
                st.session_state.approved = {i: False for i in range(len(st.session_state.scenes))}
                st.session_state.images = {}
                st.session_state.listing = None
                st.session_state.built = False
        except Exception as e:
            st.error(f"Scene planning failed: {e}")

if st.session_state.scenes:
    st.header("2 · Review the plan")
    st.caption("Edit any scene before spending money generating artwork.")
    st.session_state.scenes = [st.text_input(f"Page {i+1}", scene, key=f"scene_{i}") for i, scene in enumerate(st.session_state.scenes)]

    if st.button("🎨 Generate all pages", use_container_width=True):
        slug, project = slugify(concept), Path("books") / slug
        progress = st.progress(0, text="Starting...")
        try:
            for i, scene in enumerate(st.session_state.scenes):
                path = project / "artwork" / f"page_{i+1:02d}.png"
                progress.progress(i / len(st.session_state.scenes), text=f"Generating individual page {i+1} of {len(st.session_state.scenes)}")
                generate_page(scene, path, style)
                st.session_state.images[i] = str(path)
            save_project(project / "project.json", {"concept": concept, "scenes": st.session_state.scenes, "trim": trim, "publisher": publisher})
            progress.progress(1.0, text="Done — every page is a separate full-resolution file.")
        except Exception as e:
            st.error(f"Image generation stopped: {e}. Already-generated pages are kept so you can continue.")

if st.session_state.images:
    st.header("3 · Approve the artwork")
    st.caption("Keep the good ones. Regenerate only the page you don't like.")
    cols = st.columns(3)
    for i in range(len(st.session_state.scenes)):
        if i not in st.session_state.images:
            continue
        with cols[i % 3]:
            st.image(st.session_state.images[i], caption=f"Page {i+1}", use_container_width=True)
            st.session_state.approved[i] = st.checkbox("Approve", st.session_state.approved.get(i, False), key=f"approve_{i}")
            if st.button("🔄 Regenerate this page", key=f"regen_{i}", use_container_width=True):
                try:
                    generate_page(st.session_state.scenes[i], Path(st.session_state.images[i]), style)
                    st.session_state.approved[i] = False
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    approved_count = sum(1 for i in range(len(st.session_state.scenes)) if st.session_state.approved.get(i))
    st.progress(approved_count / len(st.session_state.scenes), text=f"{approved_count}/{len(st.session_state.scenes)} approved")

    if approved_count == len(st.session_state.scenes):
        st.header("4 · Build the complete KDP package")
        if st.button("📦 Build paperback + Kindle files", type="primary", use_container_width=True):
            slug, project = slugify(concept), Path("books") / slug
            image_paths = [Path(st.session_state.images[i]) for i in range(len(st.session_state.scenes))]
            page_count = estimated_interior_pages(len(image_paths), blank_backs)
            try:
                with st.spinner("Generating cover art, metadata, paperback files, Kindle EPUB, and ZIP..."):
                    listing = generate_listing(concept, audience, len(image_paths))
                    st.session_state.listing = listing
                    cover_art = generate_cover_art(concept, project / "cover_art.png")
                    if paperback:
                        build_paperback_interior(image_paths, project / f"{slug}_paperback_interior.pdf", trim, listing["title"], publisher, blank_backs)
                        build_paperback_cover(cover_art, project / f"{slug}_paperback_cover.pdf", trim, page_count, listing["title"], listing["subtitle"], publisher, listing["description"])
                    if kindle:
                        kindle_cover = build_kindle_cover(cover_art, project / f"{slug}_kindle_cover.jpg", listing["title"], publisher)
                        build_fixed_layout_epub(image_paths, kindle_cover, project / f"{slug}_kindle.epub", listing["title"], publisher)
                    instructions = build_listing_text(listing["title"], listing["subtitle"], listing["description"], listing["keywords"], trim, paperback, kindle, page_count)
                    (project / "KDP_LISTING.txt").write_text(instructions, encoding="utf-8")
                    make_zip(project, project / f"{slug}_complete_package.zip")
                    st.session_state.built = True
                st.success("Your publishing package is built.")
            except Exception as e:
                st.error(f"Package build failed: {e}")

if st.session_state.listing and st.session_state.built:
    listing = st.session_state.listing
    slug, project = slugify(concept), Path("books") / slug
    st.header("5 · Download + copy into KDP")
    st.text_input("Title", listing["title"])
    st.text_input("Subtitle", listing["subtitle"])
    st.text_area("Description", listing["description"], height=180)
    st.write("**7 keyword phrases**")
    for n, kw in enumerate(listing["keywords"], 1):
        st.code(f"{n}. {kw}")

    downloads = [
        (project / f"{slug}_paperback_interior.pdf", "📄 Paperback interior PDF", "application/pdf"),
        (project / f"{slug}_paperback_cover.pdf", "📕 Paperback full-wrap cover PDF", "application/pdf"),
        (project / f"{slug}_kindle.epub", "📱 Kindle fixed-layout EPUB", "application/epub+zip"),
        (project / f"{slug}_kindle_cover.jpg", "🖼️ Kindle marketing cover", "image/jpeg"),
        (project / "KDP_LISTING.txt", "📋 KDP copy/paste instructions", "text/plain"),
        (project / f"{slug}_complete_package.zip", "📦 Complete KDP package ZIP", "application/zip"),
    ]
    for path, label, mime in downloads:
        if path.exists():
            st.download_button(label, path.read_bytes(), file_name=path.name, mime=mime, use_container_width=True)

st.divider()
st.caption("Always inspect the final paperback in KDP Print Previewer and the eBook in Kindle Previewer before publishing. AI-generated artwork must be disclosed accurately when KDP asks.")
