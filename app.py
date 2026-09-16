import os
from pathlib import Path
import streamlit as st
from factory.generator import plan_scenes, generate_page, save_project
from factory.metadata import generate_listing
from factory.exporter import slugify, build_paperback_interior, build_listing_text, make_zip

st.set_page_config(page_title="Little Joy Pages Factory", page_icon="🎨", layout="wide")

DEFAULT_STYLE = """High-quality printable coloring-book line art. Cute, cozy, polished character illustration. Bold, smooth, clean black outlines on a pure white background. Full-page composition with comfortable margins. Detailed but easy and satisfying to color. Consistent character proportions and visual language across the whole book. No grayscale, no shading, no color, no page numbers, no watermark, no random text, no contact sheet, no panels, no cropped subject, no photorealism."""

try:
    if "OPENAI_API_KEY" in st.secrets:
        os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
except Exception:
    pass

for key, default in {"scenes": [], "approved": {}, "images": {}, "listing": None}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.title("🎨 Little Joy Pages Coloring Book Factory")
st.caption("Create → generate individual pages → review/regenerate → export KDP package")

with st.sidebar:
    st.header("Brand settings")
    publisher = st.text_input("Publisher / imprint", "Little Joy Pages")
    style = st.text_area("Little Joy Pages art direction", DEFAULT_STYLE, height=270)
    st.caption("Your OpenAI API key belongs in Streamlit Secrets as OPENAI_API_KEY. Never paste it into GitHub source code.")

st.header("1 · Book brief")
a, b = st.columns(2)
with a:
    concept = st.text_area("What do you want to generate?", "Cute koalas doing cozy everyday activities", height=110)
    pages = st.number_input("Coloring pages", 5, 100, 20)
    audience = st.selectbox("Audience", ["Kids", "Teens", "Adults", "Teens & adults", "All ages"], index=3)
    special = st.text_area("Must-have scenes", "Koala wearing a sleeping eye mask")
with b:
    sayings = st.checkbox("Occasional cute sayings", False)
    trim = st.selectbox("Paperback trim", ["8.5 × 11 in", "8 × 10 in", "8.25 × 8.25 in"])
    blank_backs = st.checkbox("Blank back after each coloring page", True)
    paperback = st.checkbox("Paperback", True)
    kindle = st.checkbox("Kindle / digital package", True)

if st.button("🧠 Create scene plan", type="primary", use_container_width=True):
    if not os.environ.get("OPENAI_API_KEY"):
        st.error("Add OPENAI_API_KEY to Streamlit Secrets first.")
    else:
        with st.spinner("Planning distinct pages..."):
            st.session_state.scenes = plan_scenes(concept, int(pages), audience, special, sayings)
            st.session_state.approved = {i: False for i in range(len(st.session_state.scenes))}
            st.session_state.images = {}
            st.session_state.listing = None

if st.session_state.scenes:
    st.header("2 · Scene plan")
    edited = []
    for i, scene in enumerate(st.session_state.scenes):
        edited.append(st.text_input(f"Page {i+1}", scene, key=f"scene_{i}"))
    st.session_state.scenes = edited

    if st.button("🎨 Generate all pages — one image request per page", use_container_width=True):
        slug = slugify(concept)
        project = Path("books") / slug
        progress = st.progress(0, text="Starting...")
        for i, scene in enumerate(st.session_state.scenes):
            path = project / "artwork" / f"page_{i+1:02d}.png"
            progress.progress(i / len(st.session_state.scenes), text=f"Generating page {i+1} of {len(st.session_state.scenes)}")
            generate_page(scene, path, style)
            st.session_state.images[i] = str(path)
        progress.progress(1.0, text="All pages generated as separate files.")
        save_project(project / "project.json", {"concept": concept, "scenes": st.session_state.scenes, "trim": trim, "publisher": publisher})

if st.session_state.images:
    st.header("3 · Review your coloring pages")
    st.caption("Approve good pages. Regenerate only the ones you don't like.")
    cols = st.columns(3)
    for i in range(len(st.session_state.scenes)):
        if i not in st.session_state.images:
            continue
        with cols[i % 3]:
            st.image(st.session_state.images[i], caption=f"Page {i+1}", use_container_width=True)
            st.session_state.approved[i] = st.checkbox("Approve", st.session_state.approved.get(i, False), key=f"approve_{i}")
            if st.button("🔄 Regenerate", key=f"regen_{i}", use_container_width=True):
                generate_page(st.session_state.scenes[i], Path(st.session_state.images[i]), style)
                st.session_state.approved[i] = False
                st.rerun()

    approved_count = sum(st.session_state.approved.values())
    st.progress(approved_count / len(st.session_state.scenes), text=f"{approved_count}/{len(st.session_state.scenes)} pages approved")

    if approved_count == len(st.session_state.scenes):
        st.header("4 · Build publishing package")
        if st.button("📦 Build my KDP files", type="primary", use_container_width=True):
            slug = slugify(concept)
            project = Path("books") / slug
            image_paths = [Path(st.session_state.images[i]) for i in range(len(st.session_state.scenes))]
            with st.spinner("Creating listing information and publishing files..."):
                listing = generate_listing(concept, audience, len(image_paths))
                st.session_state.listing = listing
                if paperback:
                    build_paperback_interior(image_paths, project / f"{slug}_paperback_interior.pdf", trim, listing["title"], publisher, blank_backs)
                listing_text = build_listing_text(listing["title"], listing["subtitle"], listing["description"], listing["keywords"], trim, paperback, kindle)
                (project / "KDP_LISTING.txt").write_text(listing_text, encoding="utf-8")
                if kindle:
                    (project / "KINDLE_README.txt").write_text("Kindle fixed-layout packaging is intentionally separated from the print PDF. Use the approved artwork and validate the final fixed-layout edition in Kindle Previewer before upload. A later adapter can target the current Kindle packaging toolchain without changing your approved artwork.", encoding="utf-8")
                make_zip(project, project / f"{slug}_complete_package.zip")
            st.success("Package built.")

        if st.session_state.listing:
            listing = st.session_state.listing
            st.subheader("Copy into KDP")
            st.text_input("Title", listing["title"])
            st.text_input("Subtitle", listing["subtitle"])
            st.text_area("Description", listing["description"], height=180)
            st.write("**7 keyword phrases**")
            for n, kw in enumerate(listing["keywords"], 1):
                st.code(f"{n}. {kw}")

            slug = slugify(concept)
            project = Path("books") / slug
            for path, label, mime in [
                (project / f"{slug}_paperback_interior.pdf", "Download paperback interior PDF", "application/pdf"),
                (project / "KDP_LISTING.txt", "Download KDP listing instructions", "text/plain"),
                (project / f"{slug}_complete_package.zip", "Download complete package ZIP", "application/zip"),
            ]:
                if path.exists():
                    st.download_button(label, path.read_bytes(), file_name=path.name, mime=mime, use_container_width=True)

st.divider()
st.caption("Little Joy Pages Factory keeps every coloring page as its own image file. AI-generated artwork should be disclosed accurately wherever KDP asks about AI-generated content.")
