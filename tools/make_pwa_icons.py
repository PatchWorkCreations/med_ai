from PIL import Image, ImageOps
from pathlib import Path

# --- EDIT THIS if your file lives elsewhere (Windows raw string is OK) ---
SRC = Path(r"E:\New Downloads\med_ai\myProject\myApp\static\avatar.png")

# Where to write generated icons (relative to Django static)
OUT = Path(SRC).parent.parent / "pwa" / "icons"
OUT.mkdir(parents=True, exist_ok=True)

def square_pad(img: Image.Image, fill=(0,0,0,0)):
    # Letterbox to square without cropping (keeps transparency)
    side = max(img.size)
    bg = Image.new("RGBA", (side, side), fill)
    bg.paste(img, ((side - img.width)//2, (side - img.height)//2))
    return bg

def save_png(im: Image.Image, size, name):
    out = OUT / name
    im.resize((size, size), Image.LANCZOS).save(out, format="PNG")
    print("✓", out)

def make_maskable(im: Image.Image, size=512):
    # Add safe padding (~20%) so Android mask/circles don’t clip the graphic
    base = Image.new("RGBA", (size, size), (0,0,0,0))
    margin = int(size * 0.2)
    inner = size - margin*2
    inner_img = im.resize((inner, inner), Image.LANCZOS)
    base.paste(inner_img, (margin, margin), inner_img)
    return base

img = Image.open(SRC).convert("RGBA")
img_sq = square_pad(img)

# Core PWA icons
save_png(img_sq, 192, "icon-192.png")
save_png(img_sq, 512, "icon-512.png")
mask = make_maskable(img_sq, 512)
mask.save(OUT / "maskable-512.png", "PNG")
print("✓", OUT / "maskable-512.png")

# Apple touch + favicons (nice to have)
save_png(img_sq, 180, "apple-touch-icon-180.png")
save_png(img_sq, 32,  "favicon-32.png")
save_png(img_sq, 16,  "favicon-16.png")
