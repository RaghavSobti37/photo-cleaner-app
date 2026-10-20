"""All tunable thresholds in one place. Override any of them from the CLI with --set key=value."""
from dataclasses import dataclass, fields


@dataclass
class Settings:
    # ---- analysis -------------------------------------------------------
    work_size: int = 1616            # long edge (px) every photo is analysed at; matches Sony RAW previews
    workers: int = 2                 # parallel analysis processes

    # ---- cull: bad frames ----------------------------------------------
    dark_brightness: float = 10.0    # mean grey level below this = black frame
    min_detail: float = 12.0         # 90th-percentile tile sharpness below this = no usable detail

    # ---- cull: duplicates / bursts --------------------------------------
    burst_phash: int = 5             # perceptual-hash distance for "same frame" (photo-cleaner default)
    burst_seconds: float = 120.0     # bursts must be shot within this window

    # ---- best-N per look-alike group -------------------------------------
    keep_per_group: int = 3          # how many shots to keep from each look-alike group
    similar_threshold: float = 0.55  # 0..1 combined similarity; 0.55 ~= "50% similar"
    similar_gap_seconds: float = 900 # consecutive shots further apart than this start a new group

    # ---- 360 / studio backdrop -----------------------------------------
    studio_min_fraction: float = 0.20   # share of frame that is backdrop colour
    studio_closeup_fraction: float = 0.08
    studio_closeup_top: float = 0.45    # close-ups: top band must be mostly backdrop

    # ---- faces ------------------------------------------------------------
    face_min_px: int = 45            # smaller faces are ignored when counting people in a photo
    face_id_min_px: int = 60         # faces smaller than this are not used for identity
    face_min_score: float = 0.9      # detector confidence
    face_match: float = 0.50         # SFace cosine similarity to link two faces as the same person
    library_match: float = 0.50      # similarity to a named person in the face library
    group_min_faces: int = 3         # 3+ faces = group photo
    main_person_min_photos: int = 8  # people in fewer photos go to People/Others (no naming needed)
    merge_hint: float = 0.42         # naming page suggests "same person?" above this

    @classmethod
    def from_overrides(cls, items):
        s = cls()
        types = {f.name: f.type for f in fields(cls)}
        for item in items or []:
            key, _, val = item.partition("=")
            key = key.strip()
            if key not in types:
                raise SystemExit(f"Unknown setting '{key}'. Known: {', '.join(types)}")
            cur = getattr(s, key)
            setattr(s, key, type(cur)(val))
        return s
