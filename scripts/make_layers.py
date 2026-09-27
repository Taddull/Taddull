"""Split the flat 'Reality kicks in.' illustration into animatable layers.

Outputs (public/reality/):
  plate.png        background with the headline and the clock's minute hand removed
  reality.png      "Reality" line (RGBA)
  kicks.png        "kicks in." line (RGBA)
  hub.png          red hub cap of the clock (RGBA), drawn above the vector hand
  glow_*.png       soft light masks for the TV / laptop screens
All layers are upscaled to 1920x1080 and share the same coordinate space.
"""
import os

import cv2
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'public', 'reality_src.png')
OUT = os.path.join(ROOT, 'public', 'reality')
W, H = 1920, 1080
os.makedirs(OUT, exist_ok=True)

img = np.array(Image.open(SRC).convert('RGB')).astype(np.float32)
h, w = img.shape[:2]
R, G, B = img[..., 0], img[..., 1], img[..., 2]


def smooth(x, lo, hi):
	return np.clip((x - lo) / (hi - lo), 0, 1)


# ---------------------------------------------------------------- headline
TX0, TY0, TX1, TY1 = 100, 262, 600, 505
box = np.zeros((h, w), bool)
box[TY0:TY1, TX0:TX1] = True

# Red paper: R~180, G,B < 25. Cream ink: G > 200. Black ink: R < 60.
cream_a = smooth(G, 45, 190) * box
black_a = smooth(150 - R, 0, 110) * (G < 60) * box
text_a = np.maximum(cream_a, black_a)

# Un-premultiply the ink colour against the red paper so edges stay clean.
paper = np.array([180.0, 5.0, 17.0])


def ink_layer(alpha, colour_guess):
	a = alpha[..., None]
	col = np.where(a > 0.02, (img - (1 - a) * paper) / np.maximum(a, 1e-3), colour_guess)
	col = np.clip(col, 0, 255)
	return np.dstack([col, alpha * 255]).astype(np.uint8)


# The two lines are different inks, so colour separates them. The thin dark
# fringe hugging the cream letters belongs to "Reality", not "kicks in.".
near_cream = cv2.dilate((cream_a > 0.1).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
reality_layer = ink_layer(np.maximum(cream_a, black_a * near_cream), np.array([245, 238, 228]))
kicks_layer = ink_layer(black_a * ~near_cream, np.array([15, 12, 12]))

# ---------------------------------------------------------------- clean plate
# Rebuild the headline box from the empty paper directly above it, matched to
# the average tone of the paper surrounding the box.
ph = TY1 - TY0
donor = img[TY0 - ph - 10:TY0 - 10, TX0:TX1]
ring = cv2.dilate(box.astype(np.uint8), np.ones((31, 31), np.uint8)).astype(bool) & ~box
ring &= (R > 140) & (G < 60)  # paper only (skip the building edge)
fill = img.copy()
fill[TY0:TY1, TX0:TX1] = donor - donor.reshape(-1, 3).mean(0) + img[ring].mean(0)

inner = cv2.erode(box.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32)
feather = cv2.GaussianBlur(inner, (0, 0), 3.0)
feather = np.maximum(feather, (text_a > 0.01))[..., None]
plate = img * (1 - feather) + fill * feather

# ---------------------------------------------------------------- minute hand
# The long hand is a tapered bar from the hub up-right onto the pale face.
# It is removed from the plate and redrawn as a vector in Remotion so it can tick.
HAND = np.array([[1092.5, 430.0], [1206.0, 322.5], [1218.0, 347.0], [1102.5, 441.5]])
PIVOT = np.array([1084.0, 452.0])
hand_mask = np.zeros((h, w), np.uint8)
cv2.fillConvexPoly(hand_mask, np.round(HAND * 4).astype(np.int32), 1, lineType=cv2.LINE_AA, shift=2)
hand_hole = cv2.dilate(hand_mask, np.ones((7, 7), np.uint8)).astype(bool)
# keep the black hub untouched
yy, xx = np.mgrid[0:h, 0:w]
hub_ring = ((xx - PIVOT[0]) / 16.5) ** 2 + ((yy - PIVOT[1]) / 27.5) ** 2 < 1
hand_hole &= ~hub_ring

# Fill by sliding the face texture along the direction of its shading edge,
# so the two-tone face and its grain continue straight through the gap.
along = np.array([0.33, 0.94])
along /= np.linalg.norm(along)
# The face is darker above the hand than below it, so each side of the hand
# borrows texture from its own side.
hd = (HAND[1] - HAND[0]) / np.linalg.norm(HAND[1] - HAND[0])
above = ((xx - PIVOT[0]) * hd[1] - (yy - PIVOT[1]) * hd[0]) > 0
fill = plate.astype(np.float32).copy()
done = np.zeros_like(hand_hole)
for side, shifts in ((above, (-20, -30)), (~above, (20, 30, 45))):
	for shift in shifts:
		# shifted[y, x] = plate[(x, y) + along * shift]
		M = np.float32([[1, 0, -along[0] * shift], [0, 1, -along[1] * shift]])
		shifted = cv2.warpAffine(plate.astype(np.float32), M, (w, h), borderMode=cv2.BORDER_REFLECT)
		src_in_hole = cv2.warpAffine(hand_hole.astype(np.float32), M, (w, h)) > 0.01
		take = hand_hole & side & ~done & ~src_in_hole
		fill[take] = shifted[take]
		done |= take
rest = (hand_hole & ~done).astype(np.uint8)
if rest.any():
	patched = cv2.inpaint(np.clip(fill, 0, 255).astype(np.uint8), rest, 4, cv2.INPAINT_TELEA)
	fill[rest > 0] = patched[rest > 0]
m = cv2.GaussianBlur(hand_hole.astype(np.float32), (0, 0), 1.0)[..., None]
m = np.maximum(m, hand_hole[..., None])
plate = plate * (1 - m) + fill * m
plate = np.clip(plate, 0, 255).astype(np.uint8)

# The red hub cap sits above the hand.
hub_a = smooth(R - 2 * np.maximum(G, B), 12, 40).astype(np.float32) * (((xx - PIVOT[0]) ** 2 / 16 ** 2 + (yy - PIVOT[1]) ** 2 / 26 ** 2) < 1)
hub_a = cv2.GaussianBlur(hub_a, (0, 0), 0.7)
hub_layer = np.dstack([img, hub_a * 255]).astype(np.uint8)


# ---------------------------------------------------------------- light masks
def radial(cx, cy, rx, ry):
	yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
	r = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
	a = np.exp(-r * 2.2)
	return np.dstack([np.full((h, w, 3), 255.0), a * 255]).astype(np.uint8)


glows = {
	'glow_tv': radial(751, 346, 62, 48),
	'glow_laptop': radial(713, 660, 42, 32),
	'glow_pendant': radial(803, 342, 34, 34),
	'glow_lamp_top': radial(930, 212, 40, 40),
	'glow_lamp_mid': radial(930, 378, 40, 40),
	'glow_lamp_low': radial(898, 718, 34, 34),
}


# ---------------------------------------------------------------- save @1080p
def save(arr, name):
	im = Image.fromarray(arr)
	im = im.resize((W, H), Image.LANCZOS)
	im.save(os.path.join(OUT, name + '.png'), optimize=True)


save(plate, 'plate')
save(reality_layer, 'reality')
save(kicks_layer, 'kicks')
save(hub_layer, 'hub')
for k, v in glows.items():
	save(v, k)

sx, sy = W / w, H / h
print('scale', sx, sy)
print('pivot@1080p', (PIVOT * [sx, sy]).round(2).tolist())
print('hand@1080p', (HAND * [sx, sy]).round(2).tolist())
