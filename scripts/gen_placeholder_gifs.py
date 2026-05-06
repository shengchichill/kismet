"""生成 8 個彩色佔位 GIF（各 8 幀，64x64）。"""
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    raise SystemExit("需要 Pillow：uv run --with pillow python scripts/gen_placeholder_gifs.py")

ASSETS = Path(__file__).parent.parent / "kismet" / "mage" / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

STATES = {
    "idle":     (100, 100, 180),
    "divine":   (147,  51, 234),
    "mining":   ( 34, 197,  94),
    "curse":    (239,  68,  68),
    "failed":   (249, 115,  22),
    "blessing": (234, 179,   8),
    "success":  (103, 232, 249),
    "exorcism": (168,  85, 247),
}

SIZE = 64
FRAMES = 8

for state, rgb in STATES.items():
    path = ASSETS / f"{state}.gif"
    if path.exists():
        print(f"  skip {state}.gif (exists)")
        continue
    frames = []
    for i in range(FRAMES):
        img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        pulse = int(160 + 80 * abs((i / (FRAMES - 1)) * 2 - 1))
        r = int(SIZE * 0.3 + SIZE * 0.1 * abs((i / (FRAMES - 1)) * 2 - 1))
        cx, cy = SIZE // 2, SIZE // 2
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*rgb, pulse))
        frames.append(img.convert("RGBA"))
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        loop=0,
        duration=120,
        disposal=2,
    )
    print(f"  generated {state}.gif")

print("Done.")
