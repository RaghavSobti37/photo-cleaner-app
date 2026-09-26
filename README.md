# Photo Cleaner

Private photo-cleaning utility for finding exact and visually similar photos.

## Browser app

This repository includes a Vercel-ready browser app. It keeps files private: photos are never uploaded, scanned only in the browser, and selected images download as a ZIP.

- Detects exact duplicate groups from an 8x8 perceptual hash.
- Detects visually similar photos with an adjustable threshold.
- Retains the highest-resolution photo in each group.
- Supports batches of up to 50 images, maximum 20 MB each.

## Run and verify

No install is needed to run the browser app. Serve the repository root with any static web server:

```bash
python -m http.server 8080
```

Then open `http://localhost:8080`.

```bash
npm test
npm run check
```

## Deploy to Vercel

Import `RaghavSobti37/photo-cleaner-app` in Vercel. Use the **Other** framework preset. No build command or environment variable is required; Vercel serves `index.html` directly.

## Historic local CLI

Original Python code remains in `main.py` and `backend/` for local folder-based workflows. It uses paths on the machine it runs on. Browser deployment intentionally cannot access a visitor's filesystem; each person chooses photos explicitly.

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python main.py
```
