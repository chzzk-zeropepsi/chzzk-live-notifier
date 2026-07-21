# -*- coding: utf-8 -*-
"""프로그램 로고 생성 — logo.png(256), logo.ico(멀티사이즈).

수정하고 싶으면 이 파일을 고치고 `python gen_logo.py` 재실행.
"""
from PIL import Image, ImageDraw

SIZE = 1024  # 고해상도로 그린 뒤 축소해서 안티앨리어싱

MINT_TOP = (0, 239, 176)
MINT_BOTTOM = (0, 185, 138)
WHITE = (255, 255, 255, 255)
RED = (255, 71, 87, 255)


def rounded_gradient_bg() -> Image.Image:
    """민트색 세로 그라데이션 + 둥근 사각형 마스크."""
    grad = Image.new("RGB", (1, 256))
    for y in range(256):
        t = y / 255
        grad.putpixel((0, y), tuple(
            round(a + (b - a) * t) for a, b in zip(MINT_TOP, MINT_BOTTOM)
        ))
    bg = grad.resize((SIZE, SIZE))

    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, SIZE, SIZE), radius=230, fill=255)

    out = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    out.paste(bg, (0, 0), mask)
    return out


def draw_bell(d: ImageDraw.ImageDraw):
    cx = 480  # 종을 살짝 왼쪽으로: 오른쪽 위 라이브 점 자리 확보
    d.ellipse((cx - 40, 196, cx + 40, 276), fill=WHITE)            # 꼭지
    d.pieslice((cx - 190, 250, cx + 190, 630), 180, 360, fill=WHITE)  # 돔
    d.polygon(  # 살짝 벌어지는 몸통
        [(cx - 190, 440), (cx + 190, 440), (cx + 240, 660), (cx - 240, 660)],
        fill=WHITE,
    )
    d.rounded_rectangle((cx - 250, 630, cx + 250, 706), radius=38, fill=WHITE)  # 입술
    d.ellipse((cx - 52, 726, cx + 52, 830), fill=WHITE)            # 추


def draw_live_dot(d: ImageDraw.ImageDraw):
    x, y, r = 742, 288, 118
    ring = 30
    d.ellipse((x - r - ring, y - r - ring, x + r + ring, y + r + ring), fill=WHITE)
    d.ellipse((x - r, y - r, x + r, y + r), fill=RED)


def main():
    img = rounded_gradient_bg()
    d = ImageDraw.Draw(img)
    draw_bell(d)
    draw_live_dot(d)

    logo256 = img.resize((256, 256), Image.LANCZOS)
    logo256.save("logo.png")
    logo256.save("logo.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("saved: logo.png, logo.ico")


if __name__ == "__main__":
    main()
