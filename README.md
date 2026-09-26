# Little Joy Pages Coloring Book Factory 🎨

Private Streamlit app for turning approved Little Joy Pages coloring artwork into KDP-ready publishing files.

## No-extra-cost workflow (preferred)

The production workflow does **not** require an OpenAI API key:

1. Plan the book and generate Little Joy Pages artwork in ChatGPT using the user's existing ChatGPT access.
2. Save each approved coloring page as an individual PNG/JPG.
3. Upload the approved pages to the Factory.
4. Arrange/review pages and replace any page that needs correction.
5. Upload the approved color cover artwork.
6. Export the Kindle and paperback packages.

The app should treat AI generation through an API as optional, not required. The core Factory workflow is upload → review → package → export.

## Target outputs

### Kindle first
- Fixed-layout EPUB 3 using `rendition:layout=pre-paginated`
- 1600 × 2560 JPEG marketing cover
- No unnecessary blank reverse pages

### Paperback
- Individual high-resolution PNG coloring pages
- KDP no-bleed black-and-white interior PDF
- Blank reverse side after each coloring page
- 8.5 × 11 inch trim by default
- Full-wrap paperback cover PDF with KDP bleed and calculated white-paper spine width
- Title/copyright front matter

### Publishing helper
- Suggested title and subtitle
- Ready-to-paste description
- Seven keyword phrases
- Trim/page-count/upload instructions
- AI-content disclosure reminder
- Complete ZIP containing the project assets

## Little Joy Pages art direction

Keep books visually consistent with the existing catalog: cute/kawaii rounded characters, expressive friendly faces, clean bold black outlines, pure white coloring areas, cozy scenes, enough detail to be interesting without becoming overly intricate, and polished colorful covers.

## Current book workflow

Publish Kindle first. After the Kindle title is created in KDP, use **Start your paperback** so KDP can reuse the listing metadata, then upload the separate print-ready paperback interior and wrap cover.

## Optional API mode

The repository may also support automated planning/image generation through an OpenAI API key. This is optional and should not block the upload-based workflow. Do not require the user to purchase API credits to use the Factory for packaging approved artwork.

If API mode is used, never commit a real API key to GitHub. Store secrets only in Streamlit's Secrets settings.

## KDP notes

Paperback cover dimensions for black-and-white interiors on white paper use the final page count and KDP bleed requirements. Books below 79 pages receive no spine text. Always run the finished paperback through KDP Print Previewer.

The Kindle exporter should produce a fixed-layout EPUB plus a separate marketing cover. Always validate the EPUB in Kindle Previewer before uploading.

KDP requirements can change, so verify current categories, pricing, royalties, and upload choices during publishing.

## AI disclosure

Artwork generated with generative AI should be disclosed accurately in KDP's AI-generated-content section.

## Privacy

Generated books should remain in the app runtime or user downloads and should not be committed to this repository.
