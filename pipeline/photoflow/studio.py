"""Find studio shots (plain grey / white / tinted seamless backdrop) for the 360 folder.

The backdrop colour is learned from the shoot itself: shots whose frame edges are almost entirely
smooth, low-saturation and light are taken as reference, then every photo is scored by how much
of it (overall, and in the top band for close-ups) matches that colour.
"""
import numpy as np
from PIL import Image

from .catalog import analysis_image
from .imaging import load

STUDIO = "360"


def _arrays(ws, key):
    path, manual = analysis_image(ws, key)
    if path is None:
        return None
    im = load(path, 320, ws.shots[key].get("orientation", 1) if manual else None).resize((160, 107))
    rgb = np.asarray(im).astype(float)
    g = np.asarray(im.convert("L")).astype(float)
    hsv = np.asarray(im.convert("HSV")).astype(float)
    gy, gx = np.gradient(g)
    return rgb, hsv, np.hypot(gx, gy)


def plan(ws, keys, st, log=print):
    data = {k: a for k in keys if (a := _arrays(ws, k)) is not None}
    border = np.zeros((107, 160), bool)
    border[:18], border[-18:], border[:, :18], border[:, -18:] = True, True, True, True
    refs = []
    for k, (rgb, hsv, grad) in data.items():
        neutral = (hsv[..., 1] < 45) & (hsv[..., 2] > 95) & (grad < 6)
        if neutral[border].mean() > 0.8:
            refs.append(np.median(rgb[:15].reshape(-1, 3), axis=0))
    if len(refs) < 5:
        log("No studio backdrop found in this set.")
        return {}
    c = np.median(np.array(refs), axis=0)
    chroma, level = c / (c.mean() + 1), c.mean()
    log(f"Learned studio backdrop colour RGB{tuple(int(x) for x in c)} from {len(refs)} shots")
    dest = {}
    for k, (rgb, hsv, grad) in data.items():
        lum = rgb.mean(-1)
        dist = np.linalg.norm(rgb / (lum[..., None] + 1) - chroma, axis=-1) * 100
        match = (dist < 6) & (lum > level - 60) & (lum < level + 35) & (grad < 8)
        frac, top = match.mean(), match[:20].mean()
        if frac >= st.studio_min_fraction or (frac >= st.studio_closeup_fraction and top >= st.studio_closeup_top):
            dest[k] = STUDIO
    return dest
