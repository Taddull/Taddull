#!/usr/bin/env python3
"""Generate the application icon (AppIcon.icns + 1024 px PNG) with Pillow.

Design: dark macOS-style rounded square, a film strip whose frames are grey
(preserved) with one blue frame (the revised segment) and a small green
verification check - "replace only what changed, verify everything else".
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))


def render(size: int = 1024) -> Image.Image:
    S = size * 4  # supersample for smooth edges
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = int(S * 0.09)
    radius = int(S * 0.2)
    # body with subtle vertical gradient
    body = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bd = ImageDraw.Draw(body)
    top, bottom = (40, 44, 54), (18, 19, 24)
    for y in range(pad, S - pad):
        t = (y - pad) / (S - 2 * pad)
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)) + (255,)
        bd.line([(pad, y), (S - pad, y)], fill=c)
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([pad, pad, S - pad, S - pad], radius=radius, fill=255)
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([pad, pad + S * 0.012, S - pad, S - pad + S * 0.012],
                                             radius=radius, fill=(0, 0, 0, 140))
    shadow = shadow.filter(ImageFilter.GaussianBlur(S * 0.015))
    img.alpha_composite(shadow)
    img.paste(body, (0, 0), mask)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([pad, pad, S - pad, S - pad], radius=radius, outline=(255, 255, 255, 28), width=int(S * 0.004))

    # film strip
    sx0, sx1 = int(S * 0.18), int(S * 0.82)
    sy0, sy1 = int(S * 0.36), int(S * 0.64)
    d.rounded_rectangle([sx0, sy0, sx1, sy1], radius=int(S * 0.025), fill=(10, 11, 14, 255))
    # sprocket holes
    holes = 9
    hw = (sx1 - sx0) / holes
    for i in range(holes):
        cx = sx0 + hw * (i + 0.5)
        for yy in (sy0 + (sy1 - sy0) * 0.09, sy1 - (sy1 - sy0) * 0.09):
            d.rounded_rectangle([cx - hw * 0.18, yy - S * 0.009, cx + hw * 0.18, yy + S * 0.009],
                                radius=int(S * 0.004), fill=(70, 74, 86, 255))
    # frames
    frames = 5
    fy0 = sy0 + (sy1 - sy0) * 0.2
    fy1 = sy1 - (sy1 - sy0) * 0.2
    fw = (sx1 - sx0 - S * 0.03) / frames
    for i in range(frames):
        x0 = sx0 + S * 0.015 + i * fw + S * 0.006
        x1 = x0 + fw - S * 0.012
        col = (92, 158, 255, 255) if i == 2 else (84, 88, 100, 255)
        d.rounded_rectangle([x0, fy0, x1, fy1], radius=int(S * 0.008), fill=col)
    # verification badge
    bx, by, br = int(S * 0.72), int(S * 0.70), int(S * 0.105)
    d.ellipse([bx - br, by - br, bx + br, by + br], fill=(77, 204, 135, 255), outline=(18, 19, 24, 255),
              width=int(S * 0.018))
    w = int(S * 0.024)
    d.line([(bx - br * 0.45, by + br * 0.02), (bx - br * 0.1, by + br * 0.38), (bx + br * 0.5, by - br * 0.35)],
           fill=(255, 255, 255, 255), width=w, joint="curve")
    return img.resize((size, size), Image.LANCZOS)


def main(out_dir: str = HERE) -> None:
    icon = render(1024)
    png = os.path.join(out_dir, "AppIcon.png")
    icon.save(png)
    icns = os.path.join(out_dir, "AppIcon.icns")
    icon.save(icns, sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512), (1024, 1024)])
    print(png)
    print(icns)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else HERE)
