"""Генерація VoiceType.ico для EXE та ярликів."""

from PIL import Image, ImageDraw
from pathlib import Path

# Рендеримо у великому розмірі для чіткості, потім downscale
RENDER_SIZE = 512


def make_icon(circle_color: str, mic_color: str = "white") -> Image.Image:
    s = RENDER_SIZE
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Коло
    m = int(s * 0.02)
    draw.ellipse([m, m, s - m, s - m], fill=circle_color)

    cx, cy = s // 2, s // 2

    # Головка мікрофона (rounded rect)
    mw = int(s * 0.10)
    draw.rounded_rectangle(
        [cx - mw, cy - int(s * 0.26), cx + mw, cy + int(s * 0.02)],
        radius=mw, fill=mic_color
    )

    # Дуга-тримач
    lw = max(3, s // 24)
    arc_w = int(s * 0.18)
    draw.arc(
        [cx - arc_w, cy - int(s * 0.08), cx + arc_w, cy + int(s * 0.12)],
        start=0, end=180, fill=mic_color, width=lw
    )

    # Ніжка
    leg_top = cy + int(s * 0.12)
    leg_bot = cy + int(s * 0.24)
    draw.line([cx, leg_top, cx, leg_bot], fill=mic_color, width=lw)

    # Підставка
    base_w = int(s * 0.10)
    draw.line([cx - base_w, leg_bot, cx + base_w, leg_bot], fill=mic_color, width=lw)

    return img


def main():
    out = Path(__file__).parent.parent
    icon_full = make_icon("#45475a")

    # ICO з кількома розмірами — найбільший першим
    sizes = [256, 128, 64, 48, 32, 24, 16]
    images = [icon_full.resize((s, s), Image.LANCZOS) for s in sizes]

    ico_path = out / "voicetype.ico"
    # Pillow ICO: перший image = основний, append_images = додаткові розміри
    images[0].save(ico_path, format="ICO", append_images=images[1:])
    print(f"Created {ico_path} ({', '.join(f'{s}px' for s in sizes)})")


if __name__ == "__main__":
    main()
