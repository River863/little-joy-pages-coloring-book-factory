import streamlit as st
from dataclasses import dataclass, asdict

st.set_page_config(page_title="Little Joy Pages Factory", page_icon="🎨", layout="wide")

@dataclass
class BookSpec:
    concept: str
    pages: int
    audience: str
    special_scenes: str
    sayings: bool
    paperback: bool
    kindle: bool
    trim_size: str
    blank_backs: bool

DEFAULT_STYLE = """High-quality printable coloring-book line art. Cute, cozy, polished character illustration. Bold, smooth, clean black outlines on a pure white background. Full-page composition with comfortable margins. Detailed enough to feel premium but with open spaces that are enjoyable to color. Consistent character proportions and visual language across the entire book. No grayscale, no shading, no color, no page numbers, no watermark, no random text, no contact sheet, no panels, no cropped subject, no photorealism."""

st.title("🎨 Little Joy Pages Coloring Book Factory")
st.caption("Idea → individual coloring pages → review → KDP package")

with st.sidebar:
    st.header("Little Joy Pages Style")
    st.text_area("Base art direction", DEFAULT_STYLE, height=260, key="style")
    st.divider()
    st.subheader("API")
    st.info("The deployed app will read your OpenAI API key from Streamlit secrets. Never commit API keys to GitHub.")

st.subheader("1. Create a book")
left, right = st.columns(2)
with left:
    concept = st.text_area("What book do you want?", placeholder="Cute koalas doing cozy everyday activities...", height=120)
    pages = st.number_input("Coloring pages", min_value=5, max_value=100, value=20, step=1)
    audience = st.selectbox("Audience", ["Kids", "Teens", "Adults", "Teens & adults", "All ages"], index=3)
    special = st.text_area("Must-have scenes", placeholder="Koala wearing a sleeping eye mask; reading in bed; drinking coffee; relaxing in a hammock")
with right:
    sayings = st.checkbox("Allow occasional cute sayings", value=False)
    trim = st.selectbox("Paperback trim size", ["8.5 × 11 in", "8 × 10 in", "8.25 × 8.25 in"], index=0)
    blank_backs = st.checkbox("Blank back after every coloring page", value=True)
    st.markdown("**Outputs**")
    paperback = st.checkbox("Paperback / print-ready KDP package", value=True)
    kindle = st.checkbox("Kindle / digital edition package", value=True)

if st.button("✨ Plan My Book", type="primary", use_container_width=True):
    if not concept.strip():
        st.error("Tell me what you want the book to be about first.")
    else:
        spec = BookSpec(concept, int(pages), audience, special, sayings, paperback, kindle, trim, blank_backs)
        st.session_state["book_spec"] = asdict(spec)
        st.session_state["planned"] = True

if st.session_state.get("planned"):
    st.success("Book brief saved. The next build step generates a unique scene plan and then creates every page as a separate image request/file.")
    st.subheader("2. Production pipeline")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Scenes", st.session_state["book_spec"]["pages"])
    c2.metric("Image files", st.session_state["book_spec"]["pages"])
    c3.metric("Paperback", "Yes" if st.session_state["book_spec"]["paperback"] else "No")
    c4.metric("Kindle", "Yes" if st.session_state["book_spec"]["kindle"] else "No")

    st.markdown("""
    **Pipeline:** Scene plan → Generate each image individually → Quality check → Gallery review → Regenerate weak pages → Approve → Build publishing package.

    The generation worker intentionally makes **one API image request per coloring page**. It never asks an image model to place multiple coloring pages on one canvas.
    """)

st.divider()
st.subheader("Planned KDP package")
st.write("Once artwork is approved, the app will provide individual high-resolution pages, paperback interior PDF, paperback full-wrap cover, Kindle/digital assets, listing metadata, keywords, publishing settings, and a complete ZIP package.")
