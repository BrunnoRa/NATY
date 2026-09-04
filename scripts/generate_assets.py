from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image, ImageDraw, ImageFilter


SIZES = (16, 32, 48, 128, 256)
SOURCE = PROJECT_ROOT / "assets" / "naty_source.png"


def render_icon(size: int) -> Image.Image:
    scale = 4
    canvas_size = size * scale
    image = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    margin = max(2, int(canvas_size * 0.055))
    draw.ellipse((margin, margin, canvas_size - margin, canvas_size - margin),
                 fill=(6, 15, 23, 255), outline=(24, 58, 76, 255), width=max(2, canvas_size // 42))

    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_width = max(3, canvas_size // 28)
    ring_box = (canvas_size * 0.19, canvas_size * 0.19, canvas_size * 0.81, canvas_size * 0.81)
    glow_draw.ellipse(ring_box, outline=(76, 230, 255, 190), width=glow_width * 2)
    glow = glow.filter(ImageFilter.GaussianBlur(max(1, canvas_size // 35)))
    image = Image.alpha_composite(image, glow)
    draw = ImageDraw.Draw(image)
    draw.ellipse(ring_box, outline=(85, 230, 255, 255), width=glow_width)

    for start, end in ((-68, -22), (22, 68), (112, 158), (202, 248)):
        outer = (canvas_size * 0.10, canvas_size * 0.10, canvas_size * 0.90, canvas_size * 0.90)
        draw.arc(outer, start=start, end=end, fill=(109, 247, 255, 230), width=max(2, canvas_size // 48))

    core_box = (canvas_size * 0.40, canvas_size * 0.40, canvas_size * 0.60, canvas_size * 0.60)
    draw.ellipse(core_box, fill=(100, 241, 255, 255))
    highlight = (canvas_size * 0.445, canvas_size * 0.435, canvas_size * 0.505, canvas_size * 0.495)
    draw.ellipse(highlight, fill=(225, 255, 255, 245))
    return image.resize((size, size), Image.Resampling.LANCZOS)


def render_source_icon(size: int) -> Image.Image:
    """Prepara o logo oficial para ícones nativos com cantos transparentes."""
    with Image.open(SOURCE) as opened:
        source = opened.convert("RGBA")
    edge = round(source.width * 0.027)
    radius = round(source.width * 0.20)
    mask = Image.new("L", source.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (edge, edge, source.width - edge, source.height - edge),
        radius=radius,
        fill=255,
    )
    mask = mask.filter(ImageFilter.GaussianBlur(max(1, source.width // 900)))
    source.putalpha(mask)
    resized = source.resize((size, size), Image.Resampling.LANCZOS)
    if size <= 48:
        resized = resized.filter(ImageFilter.UnsharpMask(radius=0.7, percent=125, threshold=2))
    return resized


def main() -> int:
    assets = PROJECT_ROOT / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    if not SOURCE.is_file():
        raise FileNotFoundError(f"Ícone-fonte não encontrado: {SOURCE}")
    images = {size: render_source_icon(size) for size in SIZES}
    for size, image in images.items():
        image.save(assets / f"naty_{size}.png", optimize=True)
    images[256].save(assets / "naty.ico", format="ICO", sizes=[(size, size) for size in SIZES])
    print(f"Assets gerados em {assets}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
