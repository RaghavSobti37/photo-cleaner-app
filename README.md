# Photo Cleaner

Private photo-cleaning tools for shoots:

1. **photoflow** (`pipeline/`): the full shoot-sorting workflow. Point it at a card dump or drive folder and it removes duplicates, keeps the best 3 of every look-alike group, archives bad frames, pulls studio shots into `360`, and sorts everyone into `People/<Name>` and `Group Photos`. It never deletes anything.
2. **Browser app**: a quick in-browser duplicate finder for small batches. Nothing is uploaded.
3. **Legacy CLI** (`legacy-cli/`): the original Python scoring code that photoflow is built on.

---

## photoflow: sort a shoot the same way every time

### What it does

| Step | What happens | Where it goes |
|---|---|---|
| 1. Scan | Finds every JPG/HEIC/RAW, pairs RAW+JPG into one shot, reads capture time and camera via exiftool, pulls the preview out of RAW files | n/a |
| 2. Score | photo-cleaner scoring for each shot: sharpness (Laplacian) + 100 × eyes-open/smile hits, perceptual hash, colour and layout fingerprint | `_photoflow/cache` |
| 3. Cull | Camera video thumbnails (`C0001T01.JPG`) | `Archive/Video Thumbnails` |
| | Black frames / no usable detail | `Archive/Blurry or Too Dark` |
| | Byte-identical copies (best copy stays) | `Archive/Duplicates` |
| | Bursts of the same frame | `Archive/Similar Shots (Not Best)` |
| | Look-alike groups (about 50% similar, shot back to back) trimmed to the **best 3** | `Archive/Similar Shots (Not Best)` |
| | Everything else, flattened (no date folders) | root folder |
| 4. 360 | Studio backdrop shots. The backdrop colour is learned from the shoot itself | `360/` |
| 5. Faces | 3+ clearly visible faces | `Group Photos/` |
| | 1–2 faces, filed under the biggest face | `People/<Name>` or `People/Person 012` |
| | People seen in fewer than 8 photos | `People/Others` |
| | Studio shots get the same split | `360/<Name>`, `360/Group Photos` |

Safety rules:
- **Files are only ever moved**, never deleted or overwritten. A RAW and its JPG always move together. Name clashes get ` (2)`.
- Every move is written to `_photoflow/journal.tsv`. `photoflow undo` puts everything back, and `--stage` limits the undo to one step.
- Results are cached, so a second run only analyses new photos.
- Folders are removed only if they are completely empty.

### Install (once)

```bash
cd pipeline
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m photoflow models        # downloads the two face models (~40 MB) to ~/.photoflow
```

You also need **exiftool** for capture times and RAW previews. Any of these works:
- exiftool on your PATH (`exiftool.exe` on Windows)
- the copy bundled in [sortphotos](https://github.com/RaghavSobti37/sortphotos), cloned next to this repo (it's found automatically), or passed explicitly:
  `--exiftool "perl C:/code/sortphotos/src/Image-ExifTool/exiftool"`

### Every shoot

```bash
# 1. preview what will happen (moves nothing)
python -m photoflow run "D:\Photos" --dry-run

# 2. do it
python -m photoflow run "D:\Photos"

# 3. name people: open  D:\Photos\People\_Name these people.html
#    type names -> "Download names.csv"
python -m photoflow apply-names "D:\Photos" names.csv

# changed your mind?
python -m photoflow undo "D:\Photos"                  # everything
python -m photoflow undo "D:\Photos" --stage faces    # just the face sorting
```

Run it on a whole shoot folder (all days together) so that duplicates across cards are caught.

### Naming people without naming hundreds of faces

A big event can produce 150+ distinct faces. photoflow keeps naming manageable:

1. **Only main people get a number.** Anyone who is the main face in fewer than `main_person_min_photos` (8) photos goes to `People/Others`. On a real 3,500-photo event this took the list from about 150 faces to about 50.
2. **Most important first.** The naming page is sorted by how many photos each person is in, so naming the first rows covers most photos and you can stop anytime. Blank means skip.
3. **No double naming.** When two numbers look like the same person, the card shows *"Same person as #7?"*. One click fills in `=#7` and the folders merge.
4. **Never name the same person twice across shoots.** Every name is stored in a face library (`~/.photoflow/face_library.json`). On the next shoot, known people are recognised and their folders are named automatically. Only new main people appear on the naming page.

`names.csv` can also be plain text, for example pasted from chat:

```
#1 Arjun Mehta
#2 Meera
#5 =#1          <- same person as #1
```

### Tuning

Every threshold lives in `pipeline/photoflow/config.py` and can be overridden per run:

```bash
python -m photoflow run "D:\Photos" --set keep_per_group=5 --set main_person_min_photos=4
```

| Setting | Default | Meaning |
|---|---|---|
| `keep_per_group` | 3 | Shots kept per look-alike group |
| `similar_threshold` | 0.55 | Look-alike strictness (0.55 ≈ "50% similar"; raise it to group less) |
| `similar_gap_seconds` | 900 | A pause longer than this starts a new group |
| `burst_phash` | 5 | Same-frame hash distance (photo-cleaner default) |
| `dark_brightness` / `min_detail` | 10 / 12 | What counts as a black or detail-free frame |
| `studio_min_fraction` | 0.20 | Share of the frame that must be backdrop for `360` |
| `group_min_faces` | 3 | Faces needed for `Group Photos` |
| `main_person_min_photos` | 8 | Photos needed to get your own folder |
| `face_match` / `library_match` | 0.50 | Face similarity to count as the same person |

Skip steps with `--skip studio` or `--skip faces`.

### Tests

```bash
cd pipeline && python -m unittest discover tests
```

---

## Browser app

The Vercel-ready browser app keeps files private: photos are never uploaded, they are scanned only in the browser, and selected images download as a ZIP.

- Detects exact duplicate groups from an 8x8 perceptual hash.
- Detects visually similar photos with an adjustable threshold.
- Retains the highest-resolution photo in each group.
- Supports batches of up to 50 images, maximum 20 MB each.

```bash
python -m http.server 8080        # then open http://localhost:8080
npm test
npm run check
```

Deploy: import `RaghavSobti37/photo-cleaner-app` in Vercel with the **Other** preset. No build command or environment variables are needed. `pipeline/` and `legacy-cli/` are excluded from the deployment.

## Legacy CLI

The original folder-based Python code is kept in `legacy-cli/`. photoflow reuses its scoring rules (sharpness + eyes/smiles, perceptual-hash duplicates).

```bash
cd legacy-cli
pip install -r requirements-cli.txt
python main.py
```
