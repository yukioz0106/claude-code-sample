# -*- coding: utf-8 -*-
"""ai_department 組織紹介デッキ用のイラスト調アバター画像を生成するスクリプト。

実在する人物の顔写真は使用しない（技術的に生成できないことに加え、実在しない
「AI社員」の顔として実在人物の写真を流用するのは誤認・肖像権の観点で適切でない
ため）。代わりに、各AI社員のキャラクターを表す簡易フラットイラストをPillowで
描画する。背景は透明（アルファ）にし、スライド側で役割ごとの丸背景に重ねて使う。
"""
import os
from PIL import Image, ImageDraw

OUT_DIR = os.path.join(os.path.dirname(__file__), "avatars")
os.makedirs(OUT_DIR, exist_ok=True)

SCALE = 4
SIZE = 480
CANVAS = SIZE * SCALE

CX, CY = CANVAS / 2, CANVAS * 0.56
HEAD_W, HEAD_H = CANVAS * 0.50, CANVAS * 0.56
INK = (45, 38, 34, 255)


def _ellipse(draw, cx, cy, w, h, fill):
    draw.ellipse((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), fill=fill)


def _head_and_face(draw, skin):
    # 耳
    _ellipse(draw, CX - HEAD_W / 2, CY, CANVAS * 0.07, CANVAS * 0.11, skin)
    _ellipse(draw, CX + HEAD_W / 2, CY, CANVAS * 0.07, CANVAS * 0.11, skin)
    # 頭部（顔）
    _ellipse(draw, CX, CY, HEAD_W, HEAD_H, skin)

    ey = CY - HEAD_H * 0.02
    ex_off = HEAD_W * 0.18
    r = CANVAS * 0.020
    _ellipse(draw, CX - ex_off, ey, r * 1.8, r * 2.6, INK)
    _ellipse(draw, CX + ex_off, ey, r * 1.8, r * 2.6, INK)

    blush = (224, 140, 120, 90)
    _ellipse(draw, CX - HEAD_W * 0.32, CY + HEAD_H * 0.16, CANVAS * 0.065, CANVAS * 0.038, blush)
    _ellipse(draw, CX + HEAD_W * 0.32, CY + HEAD_H * 0.16, CANVAS * 0.065, CANVAS * 0.038, blush)

    mw, mh = HEAD_W * 0.22, HEAD_H * 0.16
    draw.arc((CX - mw / 2, CY + HEAD_H * 0.12, CX + mw / 2, CY + HEAD_H * 0.12 + mh),
              start=15, end=165, fill=INK, width=int(CANVAS * 0.010))


def _save(img, name):
    img = img.resize((SIZE, SIZE), Image.LANCZOS)
    img.save(os.path.join(OUT_DIR, f"{name}.png"))
    print("saved:", name)


def make(name, skin, hair_color, hair_back=None, hair_front=None, accessory=None):
    img = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if hair_back:
        hair_back(d, hair_color)
    _head_and_face(d, skin)
    if hair_front:
        hair_front(d, hair_color)
    if accessory:
        accessory(d)
    _save(img, name)


# ---------- 髪型パーツ ----------

def short_business_hair(d, hc):
    top = CY - HEAD_H * 0.5
    d.pieslice((CX - HEAD_W * 0.56, top - HEAD_H * 0.34, CX + HEAD_W * 0.56, CY + HEAD_H * 0.08),
               180, 360, fill=hc)


def long_side_part_hair_back(d, hc):
    # 肩まで流れる後ろ髪（顔より先に描き、顔の外側に見える部分だけ残す）
    d.rounded_rectangle(
        (CX - HEAD_W * 0.62, CY - HEAD_H * 0.55, CX + HEAD_W * 0.62, CY + HEAD_H * 0.95),
        radius=CANVAS * 0.18, fill=hc,
    )


def long_side_part_hair_front(d, hc):
    top = CY - HEAD_H * 0.52
    d.pieslice((CX - HEAD_W * 0.58, top - HEAD_H * 0.28, CX + HEAD_W * 0.58, CY + HEAD_H * 0.02),
               180, 360, fill=hc)
    # 片側に流した前髪ライン
    d.polygon([
        (CX - HEAD_W * 0.10, top - HEAD_H * 0.05),
        (CX - HEAD_W * 0.30, CY - HEAD_H * 0.05),
        (CX - HEAD_W * 0.22, CY - HEAD_H * 0.02),
        (CX - HEAD_W * 0.02, top + HEAD_H * 0.02),
    ], fill=hc)


def short_tidy_hair_with_glasses(d, hc):
    top = CY - HEAD_H * 0.5
    d.pieslice((CX - HEAD_W * 0.55, top - HEAD_H * 0.30, CX + HEAD_W * 0.55, CY + HEAD_H * 0.02),
               180, 360, fill=hc)


def glasses_accessory(d):
    ey = CY - HEAD_H * 0.02
    ex_off = HEAD_W * 0.18
    rw, rh = CANVAS * 0.085, CANVAS * 0.075
    frame = (40, 40, 45, 255)
    for sign in (-1, 1):
        cx = CX + sign * ex_off
        d.ellipse((cx - rw / 2, ey - rh / 2, cx + rw / 2, ey + rh / 2), outline=frame,
                   width=int(CANVAS * 0.010))
    d.line((CX - ex_off + rw / 2 - CANVAS * 0.01, ey, CX + ex_off - rw / 2 + CANVAS * 0.01, ey),
           fill=frame, width=int(CANVAS * 0.010))
    d.line((CX - ex_off - rw / 2, ey - CANVAS * 0.01, CX - HEAD_W / 2, ey - CANVAS * 0.03),
           fill=frame, width=int(CANVAS * 0.008))
    d.line((CX + ex_off + rw / 2, ey - CANVAS * 0.01, CX + HEAD_W / 2, ey - CANVAS * 0.03),
           fill=frame, width=int(CANVAS * 0.008))


def tousled_hair(d, hc):
    top = CY - HEAD_H * 0.5
    d.pieslice((CX - HEAD_W * 0.58, top - HEAD_H * 0.32, CX + HEAD_W * 0.58, CY + HEAD_H * 0.05),
               180, 360, fill=hc)
    # 無造作な毛束（丸みのある小さなコブで柔らかく表現）
    for sign, dx in ((-1, 0.22), (0, 0.0), (1, 0.26)):
        bx = CX + sign * HEAD_W * dx
        by = top - HEAD_H * 0.16
        _ellipse(d, bx, by, CANVAS * 0.085, CANVAS * 0.07, hc)


def bob_hair_back(d, hc):
    d.rounded_rectangle(
        (CX - HEAD_W * 0.60, CY - HEAD_H * 0.50, CX + HEAD_W * 0.60, CY + HEAD_H * 0.55),
        radius=CANVAS * 0.16, fill=hc,
    )


def bob_hair_front(d, hc):
    top = CY - HEAD_H * 0.5
    d.pieslice((CX - HEAD_W * 0.57, top - HEAD_H * 0.28, CX + HEAD_W * 0.57, CY + HEAD_H * 0.02),
               180, 360, fill=hc)


def headset_accessory(d, color=(60, 60, 66, 255)):
    # ヘッドセット（耳当て＋マイク）
    d.arc((CX - HEAD_W * 0.56, CY - HEAD_H * 0.62, CX + HEAD_W * 0.56, CY + HEAD_H * 0.20),
          start=200, end=340, fill=color, width=int(CANVAS * 0.018))
    _ellipse(d, CX - HEAD_W * 0.52, CY - HEAD_H * 0.02, CANVAS * 0.05, CANVAS * 0.07, color)
    d.line((CX - HEAD_W * 0.52, CY + HEAD_H * 0.02, CX - HEAD_W * 0.18, CY + HEAD_H * 0.28),
           fill=color, width=int(CANVAS * 0.012))
    _ellipse(d, CX - HEAD_W * 0.16, CY + HEAD_H * 0.30, CANVAS * 0.035, CANVAS * 0.035, color)


PEOPLE_AVATARS = [
    dict(name="lead", skin=(232, 190, 147, 255), hair=(38, 33, 30, 255),
         hair_front=short_business_hair),
    dict(name="docs", skin=(242, 203, 163, 255), hair=(59, 42, 32, 255),
         hair_back=long_side_part_hair_back, hair_front=long_side_part_hair_front),
    dict(name="data", skin=(227, 180, 136, 255), hair=(32, 28, 26, 255),
         hair_front=short_tidy_hair_with_glasses, accessory=glasses_accessory),
    dict(name="it", skin=(239, 199, 156, 255), hair=(51, 48, 44, 255),
         hair_front=tousled_hair, accessory=lambda d: headset_accessory(d)),
    dict(name="help", skin=(244, 207, 174, 255), hair=(60, 43, 34, 255),
         hair_back=bob_hair_back, hair_front=bob_hair_front,
         accessory=lambda d: headset_accessory(d)),
]

for p in PEOPLE_AVATARS:
    make(p["name"], p["skin"], p["hair"], hair_back=p.get("hair_back"),
         hair_front=p.get("hair_front"), accessory=p.get("accessory"))
