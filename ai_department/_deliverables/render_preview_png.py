# -*- coding: utf-8 -*-
"""ai_department 組織紹介デッキをPNGとしてプレビュー表示するためのスクリプト。
PowerPointを開けない環境でも内容を確認できるように、build_org_intro_deck.py と
同じデータ（deck_data.py）を使って同じレイアウトをPillowで描画する。
"""
import os
import textwrap
from PIL import Image, ImageDraw, ImageFont
import japanize_matplotlib  # フォント(ipaexg.ttf)を取得するためだけに使用

from deck_data import (PEOPLE, ROLE_COLORS_HEX, AVATAR_BG_HEX, NAVY_HEX, BG_HEX, WHITE_HEX,
                        GRAY_TEXT_HEX, LIGHT_LINE_HEX, DANGER_HEX)

FONT_PATH = os.path.join(os.path.dirname(japanize_matplotlib.__file__), "fonts", "ipaexg.ttf")

W, H = 1920, 1080  # 13.333 x 7.5 inch @144dpi相当
HERE = os.path.dirname(__file__)
OUT_DIR = os.path.join(HERE, "preview_png")
AVATAR_DIR = os.path.join(HERE, "avatars")
os.makedirs(OUT_DIR, exist_ok=True)

_AVATAR_CACHE = {}


def load_avatar(filename):
    if filename not in _AVATAR_CACHE:
        _AVATAR_CACHE[filename] = Image.open(os.path.join(AVATAR_DIR, filename)).convert("RGBA")
    return _AVATAR_CACHE[filename]


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


NAVY = hexrgb(NAVY_HEX)
BG = hexrgb(BG_HEX)
WHITE = hexrgb(WHITE_HEX)
GRAY_TEXT = hexrgb(GRAY_TEXT_HEX)
LIGHT_LINE = hexrgb(LIGHT_LINE_HEX)
DANGER = hexrgb(DANGER_HEX)
ROLE_COLORS = {k: hexrgb(v) for k, v in ROLE_COLORS_HEX.items()}
AVATAR_BG = {k: hexrgb(v) for k, v in AVATAR_BG_HEX.items()}


def font(size, bold=False):
    # ipaexgは単一ウェイトなので太字は同フォントで代用（視覚的には太さ変化なし）
    return ImageFont.truetype(FONT_PATH, size)


def new_slide(bg=BG):
    img = Image.new("RGB", (W, H), bg)
    return img, ImageDraw.Draw(img)


def text(draw, xy, s, size, color=NAVY, align="left", max_width=None, line_spacing=1.25, anchor_mid_y=False):
    f = font(size)
    lines = []
    for raw_line in s.split("\n"):
        if max_width:
            # 文字単位での簡易折り返し（日本語は単語境界がないため1文字ずつ測る）
            cur = ""
            for ch in raw_line:
                test = cur + ch
                if draw.textlength(test, font=f) > max_width and cur:
                    lines.append(cur)
                    cur = ch
                else:
                    cur = test
            lines.append(cur)
        else:
            lines.append(raw_line)
    x, y = xy
    lh = int(size * line_spacing)
    total_h = lh * len(lines)
    if anchor_mid_y:
        y = y - total_h // 2
    for i, line in enumerate(lines):
        w = draw.textlength(line, font=f)
        lx = x
        if align == "center":
            lx = x - w / 2
        elif align == "right":
            lx = x - w
        draw.text((lx, y + i * lh), line, font=f, fill=color)
    return total_h


def rounded_rect(draw, box, radius, outline=None, fill=None, width=2):
    draw.rounded_rectangle(box, radius=radius, outline=outline, fill=fill, width=width)


def avatar(img, draw, cx, cy, d, bg_color, avatar_file, outline=WHITE):
    draw.ellipse((cx, cy, cx + d, cy + d), fill=bg_color, outline=outline, width=3)
    face = load_avatar(avatar_file).resize((d, d), Image.LANCZOS)
    img.paste(face, (int(cx), int(cy)), face)


def footer(draw, s, page, left=40):
    text(draw, (left, 1010), s, 20, color=GRAY_TEXT)
    text(draw, (1880, 1010), str(page), 20, color=GRAY_TEXT, align="right")


pages = []

# ---------- Slide 1: タイトル ----------
img, d = new_slide(NAVY)
text(d, (80, 300), "ENEOS AI社員だけの課", 30, color=(0xC9, 0xD6, 0xE8))
text(d, (80, 350), "組織紹介", 76, color=WHITE)
text(d, (80, 470), "名前を持つ5名のAI社員たちと、その役割分担", 28, color=(0xC9, 0xD6, 0xE8))
note = ("※本資料は社内説明用のイメージ資料（ドラフト）です。名称・デザインは課の管理者の確認・承認を経て確定します。\n"
        "実体はClaude Codeのサブエージェント（ai-dept-lead / ai-dept-docs / ai-dept-data / ai-dept-itsupport / ai-dept-helpdesk）であり、"
        "本資料の「名前」「顔（アバター）」は実在の人物とは関係のない演出（イラスト）です。実在人物の写真は使用していません。")
text(d, (80, 900), note, 15, color=(0x9B, 0xA9, 0xC2), max_width=1760, line_spacing=1.4)
pages.append(img)

# ---------- Slide 2: 組織体系図 ----------
img, d = new_slide(BG)
text(d, (60, 40), "組織体系図", 42, color=NAVY)
text(d, (60, 115), "課長が一次受け・振り分けを行い、専門AI社員4名が分野別に対応する（相互の直接呼び出しは行わない）", 19, color=GRAY_TEXT)

lead = PEOPLE[0]
box_w, box_h = 500, 200
lead_left = (W - box_w) // 2
lead_top = 220
rounded_rect(d, (lead_left, lead_top, lead_left + box_w, lead_top + box_h), 16, outline=ROLE_COLORS["lead"], width=3)
avatar(img, d, lead_left + 25, lead_top + 25, 150, AVATAR_BG["lead"], lead["avatar"])
text(d, (lead_left + 200, lead_top + 55), lead["name"], 26, color=NAVY)
text(d, (lead_left + 200, lead_top + 100), lead["title"], 20, color=GRAY_TEXT)

specialists = PEOPLE[1:]
n = len(specialists)
margin = 110
gap = 45
sbox_w = (W - margin * 2 - gap * (n - 1)) // n
sbox_h = 320
sbox_top = 620
mid_y = lead_top + box_h + 50

d.line((lead_left + box_w // 2, lead_top + box_h, lead_left + box_w // 2, mid_y), fill=LIGHT_LINE, width=3)
for i, p in enumerate(specialists):
    left = margin + i * (sbox_w + gap)
    cxm = left + sbox_w // 2
    d.line((lead_left + box_w // 2, mid_y, cxm, mid_y), fill=LIGHT_LINE, width=3)
    d.line((cxm, mid_y, cxm, sbox_top), fill=LIGHT_LINE, width=3)

    rounded_rect(d, (left, sbox_top, left + sbox_w, sbox_top + sbox_h), 16, outline=ROLE_COLORS[p["key"]], fill=WHITE, width=3)
    avatar(img, d, cxm - 65, sbox_top + 30, 130, AVATAR_BG[p["key"]], p["avatar"])
    text(d, (cxm, sbox_top + 190), p["name"], 24, color=NAVY, align="center")
    text(d, (cxm, sbox_top + 232), p["title"], 17, color=GRAY_TEXT, align="center", max_width=sbox_w - 30, line_spacing=1.2)

footer(d, "ai_department 組織紹介（ドラフト／管理者承認前）", 2)
pages.append(img)

# ---------- Slide 3-7: 個人プロフィール ----------
for idx, p in enumerate(PEOPLE):
    img, d = new_slide(BG)
    color = ROLE_COLORS[p["key"]]
    bar_w = 660
    d.rectangle((0, 0, bar_w, H), fill=color)

    avatar(img, d, 220, 150, 260, WHITE, p["avatar"])
    text(d, (bar_w // 2, 470), p["name"], 40, color=WHITE, align="center")
    text(d, (bar_w // 2, 528), p["kana"], 19, color=(0xE6, 0xEA, 0xF0), align="center")
    text(d, (bar_w // 2, 580), p["title"], 21, color=(0xE6, 0xEA, 0xF0), align="center")
    text(d, (bar_w // 2, 650), f"agent: {p['agent']}", 15, color=(0xCE, 0xD8, 0xE6), align="center")
    text(d, (bar_w // 2, 710), p["trait"], 16, color=(0xE6, 0xEA, 0xF0), align="center", max_width=bar_w - 100, line_spacing=1.3)
    text(d, (bar_w // 2, 870), f"「{p['motto']}」", 18, color=WHITE, align="center", max_width=bar_w - 80, line_spacing=1.3)

    rx = 720
    text(d, (rx, 70), "対応業務", 24, color=color)
    text(d, (rx, 120), p["scope"], 19, color=GRAY_TEXT, max_width=1120, line_spacing=1.3)

    text(d, (rx, 270), "できること", 24, color=color)
    y = 330
    for c in p["can"]:
        text(d, (rx, y), f"・{c}", 18, color=GRAY_TEXT, max_width=500, line_spacing=1.25)
        y += 70

    rx2 = 1290
    text(d, (rx2, 270), "対応しないこと", 24, color=DANGER)
    y = 330
    for c in p["cannot"]:
        text(d, (rx2, y), f"・{c}", 18, color=GRAY_TEXT, max_width=560, line_spacing=1.25)
        y += 70

    rounded_rect(d, (rx, 690, rx + 1120, 920), 14, outline=LIGHT_LINE, fill=(0xEC, 0xEF, 0xF3), width=2)
    text(d, (rx + 30, 715), "共通ルール：すべての成果物は依頼元に渡る前に人間が確認します。\n"
                              "機密情報・個人情報が含まれる、または疑いがある依頼は、この社員の判断で進めず人間にエスカレーションします。",
         18, color=GRAY_TEXT, max_width=1060, line_spacing=1.3)

    footer(d, "ai_department 組織紹介（ドラフト／管理者承認前）", idx + 3, left=rx)
    pages.append(img)

# ---------- Slide 8: まとめ ----------
img, d = new_slide(NAVY)
text(d, (110, 60), "人とAIの役割分担", 42, color=WHITE)

cols = [
    ("AI社員が担うこと", (0x3E, 0x7B, 0xD6), [
        "依頼内容の一次整理・分解",
        "ドラフト作成（資料／集計／スクリプト／回答案）",
        "分野間の整合性チェック",
    ]),
    ("人間が担うこと（変わらない）", (0xD6, 0x8A, 0x3E), [
        "成果物の最終確認・承認",
        "機密情報・対象外業務の最終判断",
        "本番システムへの適用・意思決定",
    ]),
]
col_w, gap_, col_h = 760, 80, 560
left0 = (W - (col_w * 2 + gap_)) // 2
for i, (head, color, items) in enumerate(cols):
    left = left0 + i * (col_w + gap_)
    rounded_rect(d, (left, 210, left + col_w, 210 + col_h), 16, outline=color, fill=(0x24, 0x35, 0x58), width=3)
    text(d, (left + 40, 240), head, 26, color=color)
    y = 330
    for it in items:
        text(d, (left + 40, y), f"・{it}", 20, color=WHITE, max_width=col_w - 80, line_spacing=1.3)
        y += 100

text(d, (110, 870), "参照：ai_department/PLAN.md（§5 セキュリティ・機密情報の取り扱い／§6 人間による承認・レビュー体制）\n"
                     "ai_department/processes/human-review.md、ai_department/processes/continuous-improvement.md",
     16, color=(0x9B, 0xA9, 0xC2), line_spacing=1.4)
pages.append(img)

# ---------- 保存 ----------
for i, img in enumerate(pages, start=1):
    path = os.path.join(OUT_DIR, f"slide_{i:02d}.png")
    img.save(path)
    print("saved:", path)
