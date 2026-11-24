# -*- coding: utf-8 -*-
"""ai_department 組織紹介PowerPoint生成スクリプト（ドラフト）。
数値データは扱わないため dataviz 的な配色規定ではなく、本スクリプト内で定義する
固定パレットを使用する。再生成したい場合はこのファイルを直接書き換えて実行する。
"""
import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
import copy
from deck_data import (PEOPLE, ROLE_COLORS_HEX, AVATAR_BG_HEX, NAVY_HEX, BG_HEX, WHITE_HEX,
                        GRAY_TEXT_HEX, LIGHT_LINE_HEX)

AVATAR_DIR = os.path.join(os.path.dirname(__file__), "avatars")


def hex_to_rgb(h):
    h = h.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


# ---------- カラーパレット ----------
NAVY = hex_to_rgb(NAVY_HEX)
BG = hex_to_rgb(BG_HEX)
WHITE = hex_to_rgb(WHITE_HEX)
GRAY_TEXT = hex_to_rgb(GRAY_TEXT_HEX)
LIGHT_LINE = hex_to_rgb(LIGHT_LINE_HEX)

ROLE_COLORS = {k: hex_to_rgb(v) for k, v in ROLE_COLORS_HEX.items()}
AVATAR_BG = {k: hex_to_rgb(v) for k, v in AVATAR_BG_HEX.items()}

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def add_bg(slide, color=BG):
    rect = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    rect.fill.solid()
    rect.fill.fore_color.rgb = color
    rect.line.fill.background()
    rect.shadow.inherit = False
    # 最背面へ
    sp = rect._element
    sp.getparent().remove(sp)
    slide.shapes._spTree.insert(2, sp)
    return rect


def add_text(slide, left, top, width, height, text, size=18, color=NAVY, bold=False,
             align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, font="Yu Gothic UI", italic=False,
             line_spacing=None):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    lines = text.split("\n")
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if line_spacing:
            p.line_spacing = line_spacing
        r = p.add_run()
        r.text = line
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.italic = italic
        r.font.name = font
        r.font.color.rgb = color
    return box


def add_avatar(slide, cx, cy, diameter, bg_color, avatar_file, outline=WHITE):
    """円形アバター。実在人物の写真ではなく、generate_avatars.py で生成したイラスト（透過PNG）を
    丸背景に重ねて表示する。"""
    circ = slide.shapes.add_shape(MSO_SHAPE.OVAL, cx, cy, diameter, diameter)
    circ.fill.solid()
    circ.fill.fore_color.rgb = bg_color
    circ.line.color.rgb = outline
    circ.line.width = Pt(2)
    circ.shadow.inherit = False
    pic = slide.shapes.add_picture(os.path.join(AVATAR_DIR, avatar_file), cx, cy, diameter, diameter)
    return circ, pic


def add_footer(slide, text="ai_department 組織紹介（ドラフト／管理者承認前）", page=None, left=Inches(0.5)):
    add_text(slide, left, Inches(7.05), Inches(10), Inches(0.4), text,
              size=10, color=GRAY_TEXT)
    if page:
        add_text(slide, Inches(12.4), Inches(7.05), Inches(0.6), Inches(0.4), str(page),
                  size=10, color=GRAY_TEXT, align=PP_ALIGN.RIGHT)


# ========== Slide 1: タイトル ==========
s = prs.slides.add_slide(BLANK)
add_bg(s, NAVY)
add_text(s, Inches(1), Inches(2.3), Inches(11.3), Inches(0.6), "ENEOS AI社員だけの課",
         size=22, color=RGBColor(0xC9, 0xD6, 0xE8), bold=True)
add_text(s, Inches(1), Inches(2.8), Inches(11.3), Inches(1.4), "組織紹介",
         size=54, color=WHITE, bold=True)
add_text(s, Inches(1), Inches(3.9), Inches(11.3), Inches(0.6),
         "名前を持つ5名のAI社員たちと、その役割分担", size=20, color=RGBColor(0xC9, 0xD6, 0xE8))
add_text(s, Inches(1), Inches(6.3), Inches(11.3), Inches(0.9),
         "※本資料は社内説明用のイメージ資料（ドラフト）です。名称・デザインは課の管理者の確認・承認を経て確定します。\n"
         "　実体はClaude Codeのサブエージェント（ai-dept-lead / ai-dept-docs / ai-dept-data / ai-dept-itsupport / ai-dept-helpdesk）であり、"
         "本資料の「名前」「顔（アバター）」は実在の人物とは関係のない演出（イラスト）です。実在人物の写真は使用していません。",
         size=11, color=RGBColor(0x9B, 0xA9, 0xC2))

# ========== Slide 2: 組織体系図 ==========
s = prs.slides.add_slide(BLANK)
add_bg(s)
add_text(s, Inches(0.6), Inches(0.35), Inches(10), Inches(0.6), "組織体系図", size=30, color=NAVY, bold=True)
add_text(s, Inches(0.6), Inches(0.95), Inches(11.5), Inches(0.4),
         "課長が一次受け・振り分けを行い、専門AI社員4名が分野別に対応する（相互の直接呼び出しは行わない）",
         size=13, color=GRAY_TEXT)

# 課長ボックス（中央上）
lead = PEOPLE[0]
box_w, box_h = Inches(3.6), Inches(1.5)
lead_left = (prs.slide_width - box_w) / 2
lead_top = Inches(1.6)
add_avatar(s, lead_left + Inches(0.15), lead_top + Inches(0.15), Inches(1.2), AVATAR_BG["lead"], lead["avatar"])
tb = add_text(s, lead_left + Inches(1.5), lead_top + Inches(0.12), box_w - Inches(1.6), box_h - Inches(0.2),
         f"{lead['name']}\n{lead['title']}", size=14, color=NAVY, bold=True, line_spacing=1.1)
box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, lead_left, lead_top, box_w, box_h)
box.fill.background()
box.line.color.rgb = ROLE_COLORS["lead"]
box.line.width = Pt(2)
box.shadow.inherit = False
box.text_frame.word_wrap = True
# 背面に送って既存テキスト/アバターを隠さないようにする
sp = box._element
box._element.getparent().remove(sp)
s.shapes._spTree.insert(2, sp)

# 4名のボックス（下段）
specialists = PEOPLE[1:]
n = len(specialists)
margin = Inches(0.7)
gap = Inches(0.35)
total_w = prs.slide_width - margin * 2
sbox_w = (total_w - gap * (n - 1)) / n
sbox_h = Inches(2.3)
sbox_top = Inches(4.3)

connector_top = lead_top + box_h
mid_y = connector_top + Inches(0.3)
# 縦線（課長から下へ）
line = s.shapes.add_connector(1, lead_left + box_w / 2, connector_top, lead_left + box_w / 2, mid_y)
line.line.color.rgb = LIGHT_LINE
line.line.width = Pt(2)

for i, p in enumerate(specialists):
    left = margin + i * (sbox_w + gap)
    # 横線（分岐）
    hline = s.shapes.add_connector(1, lead_left + box_w / 2, mid_y, left + sbox_w / 2, mid_y)
    hline.line.color.rgb = LIGHT_LINE
    hline.line.width = Pt(2)
    vline = s.shapes.add_connector(1, left + sbox_w / 2, mid_y, left + sbox_w / 2, sbox_top)
    vline.line.color.rgb = LIGHT_LINE
    vline.line.width = Pt(2)

    box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, sbox_top, sbox_w, sbox_h)
    box.fill.solid()
    box.fill.fore_color.rgb = WHITE
    box.line.color.rgb = ROLE_COLORS[p["key"]]
    box.line.width = Pt(2)
    box.shadow.inherit = False
    box.text_frame.word_wrap = True

    add_avatar(s, left + sbox_w / 2 - Inches(0.5), sbox_top + Inches(0.2), Inches(1.0), AVATAR_BG[p["key"]], p["avatar"])
    add_text(s, left + Inches(0.1), sbox_top + Inches(1.3), sbox_w - Inches(0.2), Inches(0.4),
              p["name"], size=15, color=NAVY, bold=True, align=PP_ALIGN.CENTER)
    add_text(s, left + Inches(0.1), sbox_top + Inches(1.72), sbox_w - Inches(0.2), Inches(0.55),
              p["title"], size=10.5, color=GRAY_TEXT, align=PP_ALIGN.CENTER, line_spacing=1.0)

add_footer(s, page=2)

# ========== Slide 3-7: 個人プロフィール ==========
for idx, p in enumerate(PEOPLE):
    s = prs.slides.add_slide(BLANK)
    add_bg(s)
    color = ROLE_COLORS[p["key"]]

    # 左サイドカラーバー
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(4.6), prs.slide_height)
    bar.fill.solid()
    bar.fill.fore_color.rgb = color
    bar.line.fill.background()
    bar.shadow.inherit = False

    add_avatar(s, Inches(1.6), Inches(1.0), Inches(1.8), WHITE, p["avatar"])

    add_text(s, Inches(0.4), Inches(3.1), Inches(3.8), Inches(0.5), p["name"],
              size=28, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    add_text(s, Inches(0.4), Inches(3.65), Inches(3.8), Inches(0.35), p["kana"],
              size=13, color=RGBColor(0xE6, 0xEA, 0xF0), align=PP_ALIGN.CENTER)
    add_text(s, Inches(0.4), Inches(4.1), Inches(3.8), Inches(0.5), p["title"],
              size=14, color=RGBColor(0xE6, 0xEA, 0xF0), align=PP_ALIGN.CENTER, bold=True)
    add_text(s, Inches(0.4), Inches(4.7), Inches(3.8), Inches(0.5), f"agent: {p['agent']}",
              size=10.5, color=RGBColor(0xCE, 0xD8, 0xE6), align=PP_ALIGN.CENTER, italic=True)
    add_text(s, Inches(0.4), Inches(5.15), Inches(3.8), Inches(0.85), p["trait"],
              size=11, color=RGBColor(0xE6, 0xEA, 0xF0), align=PP_ALIGN.CENTER, line_spacing=1.15)

    add_text(s, Inches(0.4), Inches(6.1), Inches(3.8), Inches(0.85), f"「{p['motto']}」",
              size=12, color=WHITE, align=PP_ALIGN.CENTER, italic=True, line_spacing=1.1)

    right_left = Inches(5.0)
    right_w = Inches(7.8)
    add_text(s, right_left, Inches(0.55), right_w, Inches(0.5), "対応業務", size=16, color=color, bold=True)
    add_text(s, right_left, Inches(1.0), right_w, Inches(1.0), p["scope"], size=13, color=GRAY_TEXT, line_spacing=1.2)

    add_text(s, right_left, Inches(2.0), Inches(3.6), Inches(0.5), "できること", size=16, color=color, bold=True)
    can_text = "\n".join(f"・{c}" for c in p["can"])
    add_text(s, right_left, Inches(2.45), Inches(3.6), Inches(2.2), can_text, size=12, color=GRAY_TEXT, line_spacing=1.25)

    add_text(s, Inches(8.9), Inches(2.0), Inches(3.9), Inches(0.5), "対応しないこと", size=16,
              color=RGBColor(0x9A, 0x2B, 0x2B), bold=True)
    cannot_text = "\n".join(f"・{c}" for c in p["cannot"])
    add_text(s, Inches(8.9), Inches(2.45), Inches(3.9), Inches(2.2), cannot_text, size=12,
              color=GRAY_TEXT, line_spacing=1.25)

    note = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, right_left, Inches(4.9), right_w, Inches(1.7))
    note.fill.solid()
    note.fill.fore_color.rgb = RGBColor(0xEC, 0xEF, 0xF3)
    note.line.color.rgb = LIGHT_LINE
    note.line.width = Pt(1)
    note.shadow.inherit = False
    add_text(s, right_left + Inches(0.25), Inches(5.05), right_w - Inches(0.5), Inches(1.4),
              "共通ルール：すべての成果物は依頼元に渡る前に人間が確認します。\n"
              "機密情報・個人情報が含まれる、または疑いがある依頼は、この社員の判断で進めず人間にエスカレーションします。",
              size=11, color=GRAY_TEXT, line_spacing=1.2)

    add_footer(s, page=idx + 3, left=Inches(5.0))

# ========== Slide 8: まとめ ==========
s = prs.slides.add_slide(BLANK)
add_bg(s, NAVY)
add_text(s, Inches(0.8), Inches(0.5), Inches(11.5), Inches(0.6), "人とAIの役割分担", size=30, color=WHITE, bold=True)

cols = [
    ("AI社員が担うこと", RGBColor(0x3E, 0x7B, 0xD6), [
        "依頼内容の一次整理・分解",
        "ドラフト作成（資料／集計／スクリプト／回答案）",
        "分野間の整合性チェック",
    ]),
    ("人間が担うこと（変わらない）", RGBColor(0xD6, 0x8A, 0x3E), [
        "成果物の最終確認・承認",
        "機密情報・対象外業務の最終判断",
        "本番システムへの適用・意思決定",
    ]),
]
col_w = Inches(5.4)
gap = Inches(0.6)
left0 = (prs.slide_width - (col_w * 2 + gap)) / 2
for i, (head, color, items) in enumerate(cols):
    left = left0 + i * (col_w + gap)
    box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, Inches(1.5), col_w, Inches(4.3))
    box.fill.solid()
    box.fill.fore_color.rgb = RGBColor(0x24, 0x35, 0x58)
    box.line.color.rgb = color
    box.line.width = Pt(2)
    box.shadow.inherit = False
    add_text(s, left + Inches(0.3), Inches(1.7), col_w - Inches(0.6), Inches(0.6), head, size=18, color=color, bold=True)
    body = "\n\n".join(f"・{it}" for it in items)
    add_text(s, left + Inches(0.3), Inches(2.4), col_w - Inches(0.6), Inches(3.2), body, size=14, color=WHITE, line_spacing=1.3)

add_text(s, Inches(0.8), Inches(6.3), Inches(11.5), Inches(0.9),
         "参照：ai_department/PLAN.md（§5 セキュリティ・機密情報の取り扱い／§6 人間による承認・レビュー体制）\n"
         "ai_department/processes/human-review.md、ai_department/processes/continuous-improvement.md",
         size=11, color=RGBColor(0x9B, 0xA9, 0xC2), line_spacing=1.2)

out_path = "/workspace/ai_department/_deliverables/ai_dept_org_introduction.pptx"
prs.save(out_path)
print("saved:", out_path)
