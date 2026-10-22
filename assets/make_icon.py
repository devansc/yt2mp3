"""Draw the yt2mp3 app icon and write assets/icon.png + assets/icon.icns.

Usage: python assets/make_icon.py   (needs Pillow; macOS for iconutil)
"""
import os
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
S = 4  # supersample factor for smooth edges
N = 1024 * S


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def draw_icon():
    img = Image.new("RGBA", (N, N), (0, 0, 0, 0))

    # macOS icon grid: 824px body centered on a 1024 canvas, ~185px corners.
    body = 824 * S
    off = (N - body) // 2
    radius = 185 * S

    # Soft drop shadow under the body.
    shadow = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (off, off + 12 * S, off + body, off + body + 12 * S), radius, fill=(0, 0, 0, 110)
    )
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(18 * S)))

    # Diagonal green gradient body.
    top, bottom = (52, 230, 120), (8, 120, 84)
    grad = Image.new("RGBA", (body, body))
    gp = grad.load()
    for y in range(0, body, S):
        for x in range(0, body, S):
            c = lerp(top, bottom, (x * 0.35 + y) / (body * 1.35)) + (255,)
            for dy in range(S):
                for dx in range(S):
                    gp[x + dx, y + dy] = c
    mask = Image.new("L", (body, body), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, body - 1, body - 1), radius, fill=255)
    img.paste(grad, (off, off), mask)

    # Beamed eighth notes (♫) in white.
    d = ImageDraw.Draw(img)
    white = (255, 255, 255, 255)
    u = S  # 1 icon pixel
    stem_w = 40 * u
    head_rx, head_ry = 92 * u, 70 * u
    left_x, right_x = 372 * u, 652 * u          # stem right edges
    beam_top_l, beam_top_r = 290 * u, 240 * u   # beam slants upward to the right
    beam_h = 92 * u
    head_y_l, head_y_r = 690 * u, 640 * u

    # Beam (parallelogram).
    d.polygon(
        [
            (left_x - stem_w, beam_top_l),
            (right_x, beam_top_r),
            (right_x, beam_top_r + beam_h),
            (left_x - stem_w, beam_top_l + beam_h),
        ],
        fill=white,
    )
    # Stems and tilted note heads.
    for sx, top_y, hy in ((left_x, beam_top_l, head_y_l), (right_x, beam_top_r, head_y_r)):
        d.rectangle((sx - stem_w, top_y + 10 * u, sx, hy), fill=white)
        head = Image.new("RGBA", (head_rx * 2 + 40 * u, head_rx * 2 + 40 * u), (0, 0, 0, 0))
        hc = head.size[0] // 2
        ImageDraw.Draw(head).ellipse(
            (hc - head_rx, hc - head_ry, hc + head_rx, hc + head_ry), fill=white
        )
        head = head.rotate(25, resample=Image.BICUBIC)
        img.alpha_composite(head, (sx - head_rx + 8 * u - hc + head_rx, hy - hc))

    return img.resize((1024, 1024), Image.LANCZOS)


def main():
    icon = draw_icon()
    icon.save(os.path.join(HERE, "icon.png"))

    iconset = os.path.join(HERE, "icon.iconset")
    shutil.rmtree(iconset, ignore_errors=True)
    os.makedirs(iconset)
    for size in (16, 32, 128, 256, 512):
        icon.resize((size, size), Image.LANCZOS).save(f"{iconset}/icon_{size}x{size}.png")
        icon.resize((size * 2, size * 2), Image.LANCZOS).save(f"{iconset}/icon_{size}x{size}@2x.png")
    subprocess.run(["iconutil", "-c", "icns", iconset, "-o", os.path.join(HERE, "icon.icns")], check=True)
    shutil.rmtree(iconset)
    print("wrote assets/icon.png and assets/icon.icns")


if __name__ == "__main__":
    main()
