# Little Joy Pages Coloring Book Factory 🎨

Private Streamlit app that turns a coloring-book idea into individual AI-generated pages and a downloadable KDP publishing package.

## What it does

1. You describe a book (for example, **Cute koalas doing cozy things**).
2. GPT plans the requested number of distinct scenes.
3. You can edit the scene list before paying for image generation.
4. The app sends **one image-generation request per page** and saves every page as its own PNG — never a contact sheet.
5. A review gallery lets you approve pages or regenerate only the ones you dislike.
6. After approval, the app creates publishing metadata and colorful cover art.
7. It exports the selected editions and one complete ZIP.

## Outputs

### Paperback
- Individual high-resolution PNG coloring pages
- KDP no-bleed black-and-white interior PDF
- Full-wrap paperback cover PDF with KDP bleed and calculated white-paper spine width
- Title/copyright front matter

### Kindle
- Fixed-layout EPUB 3 package using `rendition:layout=pre-paginated`
- 1600 × 2560 JPEG marketing cover

### Publishing helper
- Suggested title
- Subtitle
- Ready-to-paste description
- Seven keyword phrases
- Trim/page-count/upload instructions
- AI-content disclosure reminder
- Complete ZIP containing the project assets

## Current defaults

- Text planning/metadata: `gpt-5.6-terra`
- Image generation: `gpt-image-2.5-sunburst`
- 20 coloring pages
- 8.5 × 11 in paperback
- Black ink / white paper
- No bleed interior
- Blank reverse side after each coloring page
- Little Joy Pages cute/cozy line-art direction

You can override the OpenAI models with the `OPENAI_TEXT_MODEL` and `OPENAI_IMAGE_MODEL` environment variables.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
export OPENAI_API_KEY="your-key"  # Windows PowerShell: $env:OPENAI_API_KEY="your-key"
streamlit run app.py
```

## Deploy with Streamlit Community Cloud

1. Create a new Streamlit app from this private GitHub repository.
2. Set the main file to `app.py`.
3. Open the deployed app's **Settings → Secrets**.
4. Add:

```toml
OPENAI_API_KEY = "your-real-key"
```

5. Reboot the app.

Never commit the real API key. `.streamlit/secrets.toml` is ignored by Git.

## KDP notes

The app calculates paperback cover dimensions for **black-and-white interiors on white paper** using KDP's current spine formula (`page count × 0.002252 in`) and 0.125 in cover bleed. Books below 79 pages receive no spine text. Always run the finished paperback through KDP Print Previewer.

The Kindle exporter produces a fixed-layout EPUB 3 with pre-paginated metadata plus a separate marketing cover. Always validate the EPUB in Kindle Previewer before uploading.

KDP requirements can change. The app deliberately tells the publisher to verify current categories, pricing, royalties, and upload choices rather than hard-coding those business decisions.

## AI disclosure

The generated artwork is AI-generated. Answer KDP's AI-generated-content disclosure accurately during title setup.

## Privacy

Generated books live in the app runtime's `books/` directory and are ignored by Git. They are not committed to this repository.
