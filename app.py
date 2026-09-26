from pathlib import Path
import io, zipfile
import streamlit as st
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
from factory.kdp import estimated_interior_pages
from factory.exporter import slugify, build_paperback_interior, build_paperback_cover, build_fixed_layout_epub, build_listing_text, make_zip

st.set_page_config(page_title="Little Joy Pages Factory", page_icon="🎨", layout="wide")
st.title("🎨 Little Joy Pages Coloring Book Factory")
st.caption("40-page workflow · upload 8 high-quality 1×5 collages → enhance → Kindle + paperback")

with st.sidebar:
    st.header("Little Joy Pages")
    publisher=st.text_input("Publisher / imprint","Little Joy Pages")
    st.success("Free collage-to-book mode is active. No API key is required.")
    st.caption("Built for up to 40 coloring pages. The Factory splits and enhances all uploaded collages in one batch.")

st.header("1 · Book details")
a,b=st.columns(2)
with a:
    title=st.text_input("Title","Cute Hedgehogs Coloring Book")
    subtitle=st.text_input("Subtitle","40 Cozy and Adorable Hedgehog Coloring Pages")
    description=st.text_area("KDP description","A cozy collection of adorable hedgehogs enjoying sweet everyday adventures. Relax, color, and enjoy 40 cute scenes from Little Joy Pages.",height=150)
with b:
    trim=st.selectbox("Paperback trim",["8.5 × 11 in","8 × 10 in","8.25 × 8.25 in"])
    blank_backs=st.checkbox("Blank back after each paperback coloring page",True)
    paperback=st.checkbox("Build paperback files",True)
    kindle=st.checkbox("Build Kindle files",True)
    keywords_raw=st.text_area("7 keyword phrases — one per line","cute hedgehog coloring book\nhedgehog coloring pages\ncozy animal coloring book\ncute woodland animals coloring book\nadorable animal coloring pages\nrelaxing cozy coloring book\nhedgehog gifts for animal lovers",height=170)

st.header("2 · Upload ALL interior collages + cover")
st.info("For a 40-page book: upload 8 collages with 5 panels each. Select all 8 files in this one uploader. They are processed in filename order, so name them collage_01, collage_02 … collage_08.")
collages=st.file_uploader("Interior collages — upload all batches together",type=["png","jpg","jpeg"],accept_multiple_files=True)
cover=st.file_uploader("Finished COLOR front cover",type=["png","jpg","jpeg"],accept_multiple_files=False)
c1,c2,c3=st.columns(3)
with c1: grid_rows=st.number_input("Rows per collage",1,10,1,1)
with c2: grid_cols=st.number_input("Columns per collage",1,10,5,1)
with c3: crop_margin=st.slider("Trim each panel edge (%)",0.0,8.0,1.0,0.5)

st.subheader("Print enhancement")
e1,e2,e3=st.columns(3)
with e1: enhance_pages=st.checkbox("Enhance line art for print",True)
with e2: threshold=st.slider("White-background cleanup",200,250,238,1)
with e3: line_strength=st.slider("Black-line strength",1.0,2.5,1.35,0.05)

TRIM_PIXELS={"8.5 × 11 in":(2550,3300),"8 × 10 in":(2400,3000),"8.25 × 8.25 in":(2475,2475)}

def split_collage(uploaded,rows,cols,edge_pct):
    image=Image.open(uploaded).convert("RGB"); w,h=image.size; pieces=[]
    for r in range(rows):
        for c in range(cols):
            l=round(c*w/cols); rr=round((c+1)*w/cols); t=round(r*h/rows); bb=round((r+1)*h/rows)
            cw,ch=rr-l,bb-t; mx=round(cw*edge_pct/100); my=round(ch*edge_pct/100)
            pieces.append(image.crop((l+mx,t+my,rr-mx,bb-my)))
    return pieces

def enhance_line_art(panel,target_size,white_cutoff=238,strength=1.35):
    gray=ImageOps.grayscale(panel); gray=ImageOps.autocontrast(gray,cutoff=0.5); gray=ImageEnhance.Contrast(gray).enhance(strength)
    gray=gray.point(lambda p:255 if p>=white_cutoff else p)
    tw,th=target_size; scale=min(tw/gray.width,th/gray.height); nw=max(1,round(gray.width*scale)); nh=max(1,round(gray.height*scale))
    enlarged=gray.resize((nw,nh),Image.Resampling.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1.2,percent=145,threshold=3))
    canvas=Image.new("L",(tw,th),255); canvas.paste(enlarged,((tw-nw)//2,(th-nh)//2)); return canvas.convert("RGB")

raw=[]
if collages:
    collages=sorted(collages,key=lambda f:f.name.lower())
    for collage in collages: raw.extend(split_collage(collage,int(grid_rows),int(grid_cols),float(crop_margin)))

target_size=TRIM_PIXELS[trim]
enhanced=[enhance_line_art(p,target_size,int(threshold),float(line_strength)) if enhance_pages else ImageOps.pad(p.convert("RGB"),target_size,color="white",method=Image.Resampling.LANCZOS) for p in raw]

if collages:
    st.write(f"**{len(collages)} collage file(s) uploaded → {len(raw)} coloring pages detected**")
    if len(raw)==40: st.success("Perfect — all 40 coloring pages are loaded and ready.")
    elif len(raw)<40: st.warning(f"You currently have {len(raw)} pages. For this 40-page book, add {40-len(raw)} more pages before building.")
    else: st.warning(f"{len(raw)} pages detected. This exceeds the planned 40 pages; check your collage/grid settings.")

if raw:
    st.caption(f"Enhanced output: {target_size[0]} × {target_size[1]} px per page. Review the pages below before building.")
    with st.expander("Review all enhanced pages",expanded=True):
        cols=st.columns(5)
        for i,p in enumerate(enhanced):
            with cols[i%5]: st.image(p,caption=f"Page {i+1}",use_container_width=True)

if cover:
    st.write("**Front cover preview**"); st.image(cover,width=320)

st.header("3 · Optional: download individual 300-DPI pages")
if enhanced:
    page_zip=io.BytesIO()
    with zipfile.ZipFile(page_zip,"w",zipfile.ZIP_DEFLATED) as zf:
        for i,p in enumerate(enhanced,1):
            out=io.BytesIO(); p.save(out,"PNG",dpi=(300,300),optimize=True); zf.writestr(f"page_{i:02d}_300dpi.png",out.getvalue())
    st.download_button("🖼️ Download all enhanced pages (ZIP)",page_zip.getvalue(),file_name=f"{slugify(title)}_300dpi_pages.zip",mime="application/zip",use_container_width=True)

st.header("4 · Build EVERYTHING")
st.caption("One click builds the Kindle EPUB + Kindle cover + paperback interior + paperback wrap cover + KDP listing + complete ZIP.")
require_40=st.checkbox("Require exactly 40 coloring pages before building",True)
if st.button("📦 Build complete KDP package",type="primary",use_container_width=True):
    if not enhanced: st.error("Upload the interior collages first."); st.stop()
    if require_40 and len(enhanced)!=40: st.error(f"40 pages required. The Factory currently detects {len(enhanced)}. Upload all 8 five-page collages first."); st.stop()
    if not cover: st.error("Upload the finished color front cover first."); st.stop()
    slug=slugify(title); project=Path("books")/slug; artwork=project/"artwork"; artwork.mkdir(parents=True,exist_ok=True); image_paths=[]
    for i,p in enumerate(enhanced,1):
        dest=artwork/f"page_{i:02d}.png"; p.save(dest,"PNG",dpi=(300,300),optimize=True); image_paths.append(dest)
    raw_cover=project/"approved_cover.png"; Image.open(cover).convert("RGB").save(raw_cover,"PNG")
    kindle_cover=project/f"{slug}_kindle_cover.jpg"; ImageOps.fit(Image.open(raw_cover).convert("RGB"),(1600,2560),method=Image.Resampling.LANCZOS).save(kindle_cover,"JPEG",quality=95,dpi=(300,300))
    keywords=[k.strip() for k in keywords_raw.splitlines() if k.strip()][:7]
    while len(keywords)<7: keywords.append("")
    page_count=estimated_interior_pages(len(image_paths),blank_backs)
    try:
        with st.spinner("Building the complete 40-page publishing package..."):
            if kindle: build_fixed_layout_epub(image_paths,kindle_cover,project/f"{slug}_kindle.epub",title,publisher)
            if paperback:
                build_paperback_interior(image_paths,project/f"{slug}_paperback_interior.pdf",trim,title,publisher,blank_backs)
                build_paperback_cover(raw_cover,project/f"{slug}_paperback_cover.pdf",trim,page_count,title,subtitle,publisher,description)
            (project/"KDP_LISTING.txt").write_text(build_listing_text(title,subtitle,description,keywords,trim,paperback,kindle,page_count),encoding="utf-8")
            make_zip(project,project/f"{slug}_complete_package.zip")
        st.session_state["built_project"]=str(project); st.session_state["built_slug"]=slug; st.success(f"Done — complete package built from {len(image_paths)} coloring pages.")
    except Exception as e: st.error(f"Package build failed: {e}")

if st.session_state.get("built_project"):
    project=Path(st.session_state["built_project"]); slug=st.session_state["built_slug"]
    st.header("5 · Download finished KDP files")
    downloads=[(project/f"{slug}_kindle.epub","📱 Kindle EPUB","application/epub+zip"),(project/f"{slug}_kindle_cover.jpg","🖼️ Kindle cover JPG","image/jpeg"),(project/f"{slug}_paperback_interior.pdf","📄 Paperback interior PDF","application/pdf"),(project/f"{slug}_paperback_cover.pdf","📕 Paperback full-wrap cover PDF","application/pdf"),(project/"KDP_LISTING.txt","📋 KDP listing instructions","text/plain"),(project/f"{slug}_complete_package.zip","📦 COMPLETE KDP PACKAGE","application/zip")]
    for path,label,mime in downloads:
        if path.exists(): st.download_button(label,path.read_bytes(),file_name=path.name,mime=mime,use_container_width=True)

st.divider(); st.caption("40-page production workflow: 8 clean 1×5 collages + separate color cover → upload everything together → verify 40 pages → Build complete KDP package. Individual-page ZIP is optional.")