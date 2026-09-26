from pathlib import Path
import io, zipfile
import streamlit as st
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
from factory.kdp import estimated_interior_pages
from factory.exporter import slugify, build_paperback_interior, build_paperback_cover, build_fixed_layout_epub, build_listing_text, make_zip

st.set_page_config(page_title="Little Joy Pages Factory", page_icon="🎨", layout="wide")
st.title("🎨 Little Joy Pages Coloring Book Factory")
st.caption("Collage → split → line-art cleanup → 300-DPI pages → Kindle + paperback")

with st.sidebar:
    st.header("Little Joy Pages")
    publisher = st.text_input("Publisher / imprint", "Little Joy Pages")
    st.success("Free collage-to-book mode is active. No API key is required.")
    st.caption("The Factory now enhances extracted line art before creating publishing files.")

st.header("1 · Book details")
a,b=st.columns(2)
with a:
    title=st.text_input("Title","Cute Hedgehogs Coloring Book")
    subtitle=st.text_input("Subtitle","20 Cozy and Adorable Hedgehog Coloring Pages")
    description=st.text_area("KDP description","A cozy collection of adorable hedgehogs enjoying sweet everyday adventures. Relax, color, and enjoy cute scenes from Little Joy Pages.",height=150)
with b:
    trim=st.selectbox("Paperback trim",["8.5 × 11 in","8 × 10 in","8.25 × 8.25 in"])
    blank_backs=st.checkbox("Blank back after each paperback coloring page",True)
    paperback=st.checkbox("Build paperback files",True)
    kindle=st.checkbox("Build Kindle files",True)
    keywords_raw=st.text_area("7 keyword phrases — one per line","cute hedgehog coloring book\nhedgehog coloring pages\ncozy animal coloring book\ncute woodland animals coloring book\nadorable animal coloring pages\nrelaxing cozy coloring book\nhedgehog gifts for animal lovers",height=170)

st.header("2 · Upload collage(s) + cover")
st.caption("For best quality, use several smaller collages (for example four 1×5 collages) rather than one 4×5 collage. Keep every grid perfectly even and keep the color cover separate.")
collages=st.file_uploader("Coloring-page collages",type=["png","jpg","jpeg"],accept_multiple_files=True)
cover=st.file_uploader("Finished COLOR front cover",type=["png","jpg","jpeg"],accept_multiple_files=False)
c1,c2,c3=st.columns(3)
with c1: grid_rows=st.number_input("Rows per collage",1,10,1,1)
with c2: grid_cols=st.number_input("Columns per collage",1,10,5,1)
with c3: crop_margin=st.slider("Trim each panel edge (%)",0.0,8.0,1.0,0.5)

st.subheader("Print enhancement")
e1,e2,e3=st.columns(3)
with e1: enhance_pages=st.checkbox("Enhance line art for print",True)
with e2: threshold=st.slider("White-background cleanup",200,250,238,1,help="Higher values remove more light gray/grain. Lower this if thin lines disappear.")
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
    # Grayscale removes colored compression noise; autocontrast restores the full black/white range.
    gray=ImageOps.grayscale(panel)
    gray=ImageOps.autocontrast(gray,cutoff=0.5)
    gray=ImageEnhance.Contrast(gray).enhance(strength)
    # Push near-white JPEG/grain pixels to pure white without binarizing all anti-aliased edges.
    gray=gray.point(lambda p: 255 if p>=white_cutoff else p)
    # Upscale with Lanczos, then lightly sharpen outlines. Upscaling cannot invent missing detail,
    # but this produces cleaner print edges than stretching the raw collage crop inside the PDF.
    tw,th=target_size
    scale=min(tw/gray.width,th/gray.height)
    nw=max(1,round(gray.width*scale)); nh=max(1,round(gray.height*scale))
    enlarged=gray.resize((nw,nh),Image.Resampling.LANCZOS)
    enlarged=enlarged.filter(ImageFilter.UnsharpMask(radius=1.2,percent=145,threshold=3))
    canvas=Image.new("L",(tw,th),255)
    canvas.paste(enlarged,((tw-nw)//2,(th-nh)//2))
    return canvas.convert("RGB")

raw=[]
if collages:
    for collage in collages: raw.extend(split_collage(collage,int(grid_rows),int(grid_cols),float(crop_margin)))

target_size=TRIM_PIXELS[trim]
enhanced=[enhance_line_art(p,target_size,int(threshold),float(line_strength)) if enhance_pages else ImageOps.contain(p.convert("RGB"),target_size,Image.Resampling.LANCZOS) for p in raw]

if raw:
    st.write(f"**{len(raw)} individual panels detected · output {target_size[0]} × {target_size[1]} px at 300-DPI print dimensions**")
    st.caption("Spot-check Before vs Enhanced. Enhancement cleans grain and strengthens line art; it cannot recreate details absent from the original collage.")
    sample_count=min(4,len(raw))
    for i in range(sample_count):
        x,y=st.columns(2)
        with x: st.image(raw[i],caption=f"Page {i+1} · Before",use_container_width=True)
        with y: st.image(enhanced[i],caption=f"Page {i+1} · Enhanced",use_container_width=True)
    with st.expander("Review all enhanced pages",expanded=True):
        cols=st.columns(5)
        for i,p in enumerate(enhanced):
            with cols[i%5]: st.image(p,caption=f"Page {i+1}",use_container_width=True)

if cover:
    st.write("**Front cover preview**"); st.image(cover,width=320)

st.header("3 · Export enhanced individual pages")
if enhanced:
    page_zip=io.BytesIO()
    with zipfile.ZipFile(page_zip,"w",zipfile.ZIP_DEFLATED) as zf:
        for i,p in enumerate(enhanced,1):
            out=io.BytesIO(); p.save(out,"PNG",dpi=(300,300),optimize=True); zf.writestr(f"page_{i:02d}_300dpi.png",out.getvalue())
    st.download_button("🖼️ Download enhanced 300-DPI pages (ZIP)",page_zip.getvalue(),file_name=f"{slugify(title)}_300dpi_pages.zip",mime="application/zip",use_container_width=True)

st.header("4 · Build KDP files")
if st.button("📦 Build my KDP package",type="primary",use_container_width=True):
    if not enhanced: st.error("Upload at least one coloring-page collage first."); st.stop()
    if not cover: st.error("Upload the finished color front cover first."); st.stop()
    slug=slugify(title); project=Path("books")/slug; artwork=project/"artwork"; artwork.mkdir(parents=True,exist_ok=True)
    image_paths=[]
    for i,p in enumerate(enhanced,1):
        dest=artwork/f"page_{i:02d}.png"; p.save(dest,"PNG",dpi=(300,300),optimize=True); image_paths.append(dest)
    raw_cover=project/"approved_cover.png"; Image.open(cover).convert("RGB").save(raw_cover,"PNG")
    kindle_cover=project/f"{slug}_kindle_cover.jpg"; ImageOps.fit(Image.open(raw_cover).convert("RGB"),(1600,2560),method=Image.Resampling.LANCZOS).save(kindle_cover,"JPEG",quality=95,dpi=(300,300))
    keywords=[k.strip() for k in keywords_raw.splitlines() if k.strip()][:7]
    while len(keywords)<7: keywords.append("")
    page_count=estimated_interior_pages(len(image_paths),blank_backs)
    try:
        with st.spinner("Building enhanced Kindle + paperback files..."):
            if kindle: build_fixed_layout_epub(image_paths,kindle_cover,project/f"{slug}_kindle.epub",title,publisher)
            if paperback:
                build_paperback_interior(image_paths,project/f"{slug}_paperback_interior.pdf",trim,title,publisher,blank_backs)
                build_paperback_cover(raw_cover,project/f"{slug}_paperback_cover.pdf",trim,page_count,title,subtitle,publisher,description)
            (project/"KDP_LISTING.txt").write_text(build_listing_text(title,subtitle,description,keywords,trim,paperback,kindle,page_count),encoding="utf-8")
            make_zip(project,project/f"{slug}_complete_package.zip")
        st.session_state["built_project"]=str(project); st.session_state["built_slug"]=slug; st.success("Done! Enhanced KDP package is ready.")
    except Exception as e: st.error(f"Package build failed: {e}")

if st.session_state.get("built_project"):
    project=Path(st.session_state["built_project"]); slug=st.session_state["built_slug"]
    st.header("5 · Download finished publishing files")
    downloads=[(project/f"{slug}_kindle.epub","📱 Kindle EPUB","application/epub+zip"),(project/f"{slug}_kindle_cover.jpg","🖼️ Kindle cover JPG","image/jpeg"),(project/f"{slug}_paperback_interior.pdf","📄 Paperback interior PDF","application/pdf"),(project/f"{slug}_paperback_cover.pdf","📕 Paperback full-wrap cover PDF","application/pdf"),(project/"KDP_LISTING.txt","📋 KDP listing instructions","text/plain"),(project/f"{slug}_complete_package.zip","📦 Complete package ZIP","application/zip")]
    for path,label,mime in downloads:
        if path.exists(): st.download_button(label,path.read_bytes(),file_name=path.name,mime=mime,use_container_width=True)

st.divider()
st.caption("QUALITY TIP: four 1×5 collages are preferred over one 4×5 collage because each source panel receives substantially more pixels. Always inspect the enhanced pages at full size and preview the final paperback in KDP Print Previewer before publishing.")