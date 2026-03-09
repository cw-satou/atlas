import os
import json
import re
import random
from openai import OpenAI
from collections import Counter


# APIキーの取得
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY")


if PERPLEXITY_API_KEY:
    client = OpenAI(
        api_key=PERPLEXITY_API_KEY,
        base_url="https://api.perplexity.ai"
    )
else:
    client = None


# 天然石オラクルカードの定義
# 天然石オラクルカードの定義（メイン石のみ）
CRYSTAL_ORACLE_CARDS = [
    {
        "name": "アメジスト", "en": "Amethyst crystal",
        "meaning_up": "精神の安定・直感の覚醒", "meaning_rev": "不安・逃避・考えすぎ"
    },
    {
        "name": "ラピスラズリ", "en": "Lapis Lazuli crystal",
        "meaning_up": "真実・洞察・精神性の成長", "meaning_rev": "自己不信・コミュニケーションの滞り"
    },
    {
        "name": "カーネリアン・サードニクス", "en": "Carnelian Sardonyx crystal",
        "meaning_up": "行動力・情熱・自己表現", "meaning_rev": "衝動・エネルギーの空回り"
    },
    {
        "name": "マラカイト", "en": "Malachite crystal",
        "meaning_up": "深い癒やし・感情の解毒", "meaning_rev": "感情の停滞・過去への執着"
    },
    {
        "name": "アイリスクォーツ", "en": "Iris Quartz crystal",
        "meaning_up": "希望・再生・波動の調整", "meaning_rev": "気力不足・未来への不安"
    },
]

STOCK_STONES = {
    # メイン候補（10mm / 12mm）
    "ラピスラズリ": {
        "size": 10,
        "code": "G516-6H785",
        "role": "main",
        "color": "blue"
    },
    "カーネリアン・サードニクス": {
        "size": 10,
        "code": "G1096-H9127",
        "role": "main",
        "color": "orange"
    },
    "マラカイト": {
        "size": 10,
        "code": "N294-MCT10",
        "role": "main",
        "color": "green"
    },
    "アイリスクォーツ": {
        "size": 12,
        "code": "N780-7283M",
        "role": "main",
        "color": "clear"
    },
    "アメジスト": {
        "size": 10,
        "code": "N477-8824X",
        "role": "main",
        "color": "purple"
    },

    # サブ候補（8mm & 10mm）
    "シーブルーカルセドニー": {
        "size": 8,
        "code": "CC359-01RA/#1",
        "role": "sub",
        "color": "light_blue"
    },
    "マダガスカル産ローズクォーツ": {
        "size": 8,
        "code": "N560-V4534",
        "role": "sub",
        "color": "pink"
    },
    "グレークォーツ": {
        "size": 10,
        "code": "G264-3836G",
        "role": "sub",   # ★ここを main→sub に変更
        "color": "gray"
    },
}

MAIN_TO_SUB_MAP = {
    "purple": ["マダガスカル産ローズクォーツ", "シーブルーカルセドニー", "グレークォーツ"],
    "blue":   ["シーブルーカルセドニー", "グレークォーツ"],
    "orange": ["マダガスカル産ローズクォーツ", "グレークォーツ"],
    "green":  ["シーブルーカルセドニー", "グレークォーツ"],
    "clear":  ["マダガスカル産ローズクォーツ", "シーブルーカルセドニー", "グレークォーツ"],
    "gray":   ["マダガスカル産ローズクォーツ", "シーブルーカルセドニー"],
}

PRODUCT_MAP = {

    # 水エレメント
    ("water", "love", "seiban"): {"name": "星盤 / 蒼海の恋", "slug": "seiban-ocean-love"},
    ("water", "heal", "seiban"): {"name": "星盤 / 月海のやすらぎ", "slug": "seiban-ocean-heal"},
    ("water", "action", "seiban"): {"name": "星盤 / 蒼海の勇気", "slug": "seiban-ocean-courage"},
    ("water", "intuition", "seiban"): {"name": "星盤 / 水鏡のひらめき", "slug": "seiban-ocean-insight"},

    ("water", "love", "kisei"): {"name": "輝星 / 蒼海の恋", "slug": "kisei-ocean-love"},
    ("water", "heal", "kisei"): {"name": "輝星 / 月海のやすらぎ", "slug": "kisei-ocean-heal"},
    ("water", "action", "kisei"): {"name": "輝星 / 蒼海の勇気", "slug": "kisei-ocean-courage"},
    ("water", "intuition", "kisei"): {"name": "輝星 / 水鏡のひらめき", "slug": "kisei-ocean-insight"},


    # 火エレメント
    ("fire", "love", "seiban"): {"name": "星盤 / 紅炎の恋", "slug": "seiban-flame-love"},
    ("fire", "heal", "seiban"): {"name": "星盤 / 焔のやすらぎ", "slug": "seiban-flame-heal"},
    ("fire", "action", "seiban"): {"name": "星盤 / 太陽の勇気", "slug": "seiban-solar-courage"},
    ("fire", "intuition", "seiban"): {"name": "星盤 / 炎のひらめき", "slug": "seiban-flame-insight"},

    ("fire", "love", "kisei"): {"name": "輝星 / 紅炎の恋", "slug": "kisei-flame-love"},
    ("fire", "heal", "kisei"): {"name": "輝星 / 焔のやすらぎ", "slug": "kisei-flame-heal"},
    ("fire", "action", "kisei"): {"name": "輝星 / 太陽の勇気", "slug": "kisei-solar-courage"},
    ("fire", "intuition", "kisei"): {"name": "輝星 / 炎のひらめき", "slug": "kisei-flame-insight"},


    # 風エレメント
    ("wind", "love", "seiban"): {"name": "星盤 / 星風の恋", "slug": "seiban-wind-love"},
    ("wind", "heal", "seiban"): {"name": "星盤 / 風花のやすらぎ", "slug": "seiban-wind-heal"},
    ("wind", "action", "seiban"): {"name": "星盤 / 疾風の勇気", "slug": "seiban-wind-courage"},
    ("wind", "intuition", "seiban"): {"name": "星盤 / 蒼空のひらめき", "slug": "seiban-wind-insight"},

    ("wind", "love", "kisei"): {"name": "輝星 / 星風の恋", "slug": "kisei-wind-love"},
    ("wind", "heal", "kisei"): {"name": "輝星 / 風花のやすらぎ", "slug": "kisei-wind-heal"},
    ("wind", "action", "kisei"): {"name": "輝星 / 疾風の勇気", "slug": "kisei-wind-courage"},
    ("wind", "intuition", "kisei"): {"name": "輝星 / 蒼空のひらめき", "slug": "kisei-wind-insight"},


    # 地エレメント
    ("earth", "love", "seiban"): {"name": "星盤 / 深森の恋", "slug": "seiban-earth-love"},
    ("earth", "heal", "seiban"): {"name": "星盤 / 大地のやすらぎ", "slug": "seiban-earth-heal"},
    ("earth", "action", "seiban"): {"name": "星盤 / 岩の勇気", "slug": "seiban-earth-courage"},
    ("earth", "intuition", "seiban"): {"name": "星盤 / 森羅のひらめき", "slug": "seiban-earth-insight"},

    ("earth", "love", "kisei"): {"name": "輝星 / 深森の恋", "slug": "kisei-earth-love"},
    ("earth", "heal", "kisei"): {"name": "輝星 / 大地のやすらぎ", "slug": "kisei-earth-heal"},
    ("earth", "action", "kisei"): {"name": "輝星 / 岩の勇気", "slug": "kisei-earth-courage"},
    ("earth", "intuition", "kisei"): {"name": "輝星 / 森羅のひらめき", "slug": "kisei-earth-insight"}

}
STONE_SIZES = {
    "main10": 10,
    "main12": 12,
    "bead8": 8,
    "spacer5": 5,
    "spacer2": 2
}

ELEMENT_PREFIX = {
    "water": ["星海", "蒼海", "月海", "深海"],
    "fire": ["紅炎", "焔", "太陽", "烈火"],
    "wind": ["蒼風", "星風", "天空", "疾風"],
    "earth": ["大地", "深森", "原石", "蒼岩"]
}

THEME_SUFFIX = {
    "love": ["の恋", "の絆", "の愛"],
    "heal": ["のやすらぎ", "の癒し", "の静寂"],
    "action": ["の勇気", "の前進", "の意志"],
    "intuition": ["のひらめき", "の導き", "の叡智"]
}

IMAGE_CACHE = {}

def bracelet_length(inner_size):
    return inner_size * 10 + 10


def fixed_length(main_size):

    main_total = main_size * 2
    spacer_total = 5 * 3

    return main_total + spacer_total


def calculate_8mm_with_spacers(inner_size, main_size):

    total = bracelet_length(inner_size)

    fixed = fixed_length(main_size)

    remain = total - fixed

    beads8 = 0
    spacer2 = 0
    used = 0

    while True:

        if beads8 % 3 == 0 and beads8 != 0:
            if used + 2 > remain:
                break
            used += 2
            spacer2 += 1

        if used + 8 > remain:
            break

        used += 8
        beads8 += 1

    return {
        "8mm": beads8,
        "spacer2": spacer2
    }


ELEMENT_NAMES = {
    "water": ["蒼海", "月海", "星海"],
    "fire": ["紅炎", "太陽", "焔"],
    "wind": ["蒼風", "星風", "天空"],
    "earth": ["大地", "深森"]
}

THEME_NAMES = {
    "love": "の恋",
    "heal": "のやすらぎ",
    "action": "の勇気",
    "intuition": "のひらめき"
}

ELEMENT_EN = {
    "water": "Ocean",
    "fire": "Flame",
    "wind": "Wind",
    "earth": "Earth"
}

THEME_EN = {
    "love": "Love",
    "heal": "Serenity",
    "action": "Courage",
    "intuition": "Insight"
}


def choose_product(element, theme, gender, kiraboshi=False):

    key = (element, theme, gender)

    product = PRODUCT_MAP.get(key)

    if not product:
        return None

    name = product["name"]
    slug = product["slug"]

    if kiraboshi:
        name = f"輝星 / {name}"
        slug = f"{slug}-kiraboshi"

    return {
        "product_name": name,
        "product_slug": slug
    }


def choose_theme(concerns):

    if not concerns:
        return "love"

    if "恋愛" in concerns:
        return "love"

    if "健康" in concerns:
        return "heal"

    if "仕事" in concerns:
        return "action"

    if "金運" in concerns:
        return "action"

    return "intuition"


def normalize_gender(g):

    if g == "男性":
        return "m"

    return "f"


def generate_bracelet_name_en(element, theme):

    el = ELEMENT_EN.get(element, "Star")
    th = THEME_EN.get(theme, "Light")

    return f"{el} {th}"


def generate_bracelet_image(layout):

    key = "-".join(layout)

    if key in IMAGE_CACHE:
        return IMAGE_CACHE[key]

    stones = ", ".join(layout)

    prompt = f"""
realistic gemstone bracelet jewelry photography
beads: {stones}
natural crystal bracelet
studio lighting
white background
product photo
"""

    resp = client.chat.completions.create(
        model="nanobanana2",
        messages=[
            {"role": "system", "content": "You generate product image prompts."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4
    )

    image_url = resp.choices[0].message.content

    return image_url


def generate_bracelet_name(element, theme):

    prefix_list = ELEMENT_PREFIX.get(element, ["星"])
    suffix_list = THEME_SUFFIX.get(theme, ["の光"])

    prefix = random.choice(prefix_list)
    suffix = random.choice(suffix_list)

    return prefix + suffix


def generate_bracelet_design(result, inner_size, element="water", theme="love"):
    series = "kisei" if result.get(
        "bracelet_type") == "birth_top_element_side" else "seiban"
    product = PRODUCT_MAP[(element, theme, series)]

    product_name = product["name"]
    product_slug = product["slug"]
    name = generate_bracelet_name(element, theme)
    name_en = generate_bracelet_name_en(element, theme)

    main = result["stones_main"][0]
    sub = result["stones_sub"][0]

    main_name = main["name"]
    main_size = STOCK_STONES.get(main_name, {}).get("size", 10)
    sub_name = sub["name"] if sub else "水晶"

    # 8mm石の計算
    calc = calculate_8mm_with_spacers(inner_size, main_size)

    beads8 = calc["8mm"]
    spacer2 = calc["spacer2"]

    # レイアウト生成
    layout = generate_bracelet_layout(
        main_name,
        sub_name,
        beads8,
        spacer2
    )

    # 石カウント
    stone_counts = count_stones(layout)

    # 画像生成
    image_data = generate_bracelet_image(layout)

    return {
        "product_name": product_name,
        "product_slug": product_slug,
        "bracelet_name": name,
        "bracelet_name_en": name_en,
        "size": inner_size,
        "main_stone": main_name,
        "main_size": main_size,
        "layout": layout,
        "stone_counts": stone_counts,
        "8mm_beads": beads8,
        "2mm_spacers": spacer2,
        "5mm_spacers": 3,
        "image": image_data
    }

def count_stones(layout):
    return dict(Counter(layout))


SYSTEM_PROMPT = """
あなたは、西洋占星術とクリスタルヒーリングに精通したプロの占い師です。
ユーザーの悩みに寄り添い、希望を与え、まずは「相性の良い石の種類」を提案してください。

【出力形式の絶対ルール】
1. JSON形式のみを出力すること。Markdownのコードブロックは不要。
2. 引用表記（[1]など）は削除すること。
3. ユーザーの「悩み詳細」を深く読み取り、共感のこもった鑑定を行うこと。
4. この段階ではブレスレットの個数・配置は決めず、「あなたにマッチする石」だけを提案します。
5. 各セクションは指定文字数を目安に、過不足なく簡潔に書いてください。
6. 【】のような見出しマークは一切使わず、自然な文章だけで書いてください。
7. 重要な箇所は**で囲って強調してください。例：「あなたの運命の石は**アメジスト**です。」のように、**で囲むことで、フロント側で強調表示がしやすくなります。
8. 全体で日本語で500文字を超えないようにしてください。
9. 「。」の後には必ず改行を2つ入れて読みやすいようにしてください。
10. destiny_map では、可能であれば出生時間・出生地も活かして、
   「生まれた時間帯（早朝・昼・夕方・深夜など）」や
   「生まれた土地のイメージ（海沿いの街、雪の多い地域など）」から感じられる
   人生の舞台設定や雰囲気についても1段落程度で触れてください。
   占星術用語を使いすぎず、一般の人に分かりやすい言葉でやさしく表現してください。
"""

AVAILABLE_STONES = """
- アメジスト
- ラピスラズリ
- カーネリアン・サードニクス
- マラカイト
- アイリスクォーツ
- シーブルーカルセドニー
- マダガスカル産ローズクォーツ
- グレークォーツ
"""

# AVAILABLE_STONES = """
# - アメジスト（紫）
# - ローズクォーツ（ピンク）
# - シトリン（黄）
# - 水晶（透明）
# - オニキス（黒）
# - アクアマリン（水色）
# - ラピスラズリ（紺）
# - タイガーアイ（茶金）
# - ムーンストーン（白）
# - カーネリアン（赤）
# """


def generate_bracelet_layout(main_stones, sub_stones, beads8, spacer2):

    main = main_stones[0]["name"]
    sub = sub_stones[0]["name"] if sub_stones else "水晶"

    half_beads = beads8 // 2
    half_spacers = spacer2 // 2

    pattern = []

    bead_counter = 0
    spacer_counter = 0

    for i in range(half_beads):

        if i == half_beads // 2:
            pattern.append(main)
        else:
            pattern.append(sub)

        bead_counter += 1

        # 3〜4石ごとにスペーサー
        if bead_counter % 3 == 0 and spacer_counter < half_spacers:
            pattern.append("spacer2")
            spacer_counter += 1

    center = ["spacer5", main, "spacer5"]

    layout = pattern + center + pattern[::-1]

    layout.append("spacer5")

    return layout


def generate_today_fortune(user_input: dict) -> str:
    """生年月日・出生時間・出生地を使って「今日の運勢」を生成"""
    if not client:
        return "今日は、自分のペースを大切に過ごすと良さそうな日です。"

    birth = user_input.get("birth", {})
    gender = user_input.get("gender", "指定なし")

    system_prompt = """
あなたは、西洋占星術とクリスタルヒーリングに精通したプロの占い師です。
生年月日・生まれた時間・生まれた場所から、その日の流れを読み解き、
やさしく希望が持てる「今日の運勢」を1メッセージで伝えてください。

【出力形式の絶対ルール】
1. JSON形式のみを出力すること。Markdownのコードブロックは不要。
2. 引用表記（[1]など）は削除すること。
3. ユーザーの「悩み詳細」を深く読み取り、共感のこもった鑑定を行うこと。
4. この段階ではブレスレットの個数・配置は決めず、「あなたにマッチする石」だけを提案します。
5. 各セクションは指定文字数を目安に、過不足なく簡潔に書いてください。
6. 【】のような見出しマークは一切使わず、自然な文章だけで書いてください。
7. 重要な箇所は**で囲って強調してください。例：「あなたの運命の石は**アメジスト**です。」
8. 全体で日本語で500文字を超えないようにしてください。
9. 「。」の後には必ず改行を2つ入れて読みやすいようにしてください。
"""

    user_prompt = f"""
以下の情報から、今日一日の運勢と過ごし方のヒントを日本語で1メッセージだけ生成してください。

[ユーザー情報]
- 性別: {gender}
- 生年月日: {birth.get('date', '不明')}
- 出生時間: {birth.get('time', '不明')}
- 出生地: {birth.get('place', '不明')}

[出力条件]
- 1段落の目安は100バイト前後。3段落で構成してください。段落と段落の間に１つ改行を入れること。
- 最初に入力された情報の復唱と星座やエレメントの解釈
- 以降は、生年月日の観点、生まれた場所の観点、生まれた時間の観点など、複数の角度から今日の運勢を読み解いてください。
- 「今日のあなたは…」のように、今日一日の雰囲気と、どう過ごすと良いかのヒントを必ず入れてください。
- 生まれた時間帯や生まれた場所の雰囲気から感じられる「人生の舞台設定」や、その日の星の流れに少し触れても構いません。
- 専門用語を多用せず、占星術に詳しくない人にも分かる言葉で書いてください。
- 箇条書きや【】の見出し、絵文字、記号は使わず、自然な文章1つだけにしてください。
- JSONや説明文は不要です。占い結果の本文だけを返してください。
"""

    resp = client.chat.completions.create(
        model="sonar-pro",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",  "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=400,
    )

    content = resp.choices[0].message.content.strip()
    return content


def create_user_prompt(user_input, oracle_result):
    """ユーザー情報とオラクル結果からプロンプトを生成"""
    birth = user_input.get('birth', {})
    concerns = user_input.get('concerns', [])
    problem_text = user_input.get('problem', '')

    # オラクル結果の文字列作成
    position_str = "正位置" if oracle_result['is_upright'] else "逆位置"
    oracle_text = f"カード: {oracle_result['card']['name']}\n状態: {position_str}\n意味: {oracle_result['meaning']}"

    # 悩みカテゴリを文字列に
    concerns_text = "、".join(concerns) if concerns else "指定なし"

    return f"""
以下のユーザー情報と、先ほど引いた「天然石オラクルカード」の結果に基づき、鑑定を行ってください。

【オラクルカード結果】
{oracle_text}

【ユーザー情報】
- 性別: {user_input.get('gender', '指定なし')}
- 悩みのカテゴリ: {concerns_text}
- 具体的な悩み: {problem_text if problem_text else '指定なし'}
- 生年月日: {birth.get('date', '不明')}
- 出生時間: {birth.get('time', '不明')}
- 出生地: {birth.get('place', '不明')}

【使用可能な石リスト】
{AVAILABLE_STONES}

【出力JSONスキーマ】

{{
  "destiny_map": "全体のテーマ・運命の地図を120文字程度で。【】見出しは絶対に使わず、自然な文章だけで書いてください。重要な言葉は**で囲んで強調。",
  "past": "生まれ持った資質・これまでの流れを80文字程度で。【】見出しは絶対に使わず、自然な文章だけで書いてください。重要な言葉は**で囲んで強調。",
  "present_future": "今の課題・これからのテーマを120文字程度で。【】見出しは絶対に使わず、自然な文章だけで書いてください。重要な言葉は**で囲んで強調。",
  "element_diagnosis": "火・地・風・水のバランスと不足要素、アドバイスを80文字程度で。【】見出しは絶対に使わず、自然な文章だけで書いてください。重要な言葉は**で囲んで強調。",
  "oracle_message": "引いたカード「{oracle_result['card']['name']}」の{position_str}の詳細メッセージを100文字程度で。【】見出しは絶対に使わず、自然な文章だけで書いてください。重要な言葉は**で囲んで強調。",
  "bracelet_proposal": "どんな意図で石を選び、どんな願いをサポートするか、80文字程度で。【】見出しは絶対に使わず、自然な文章だけで書いてください。重要な言葉は**で囲んで強調。",
  "stone_support_message": "あなたはこういう状況であなたにはこういう石の魔法のサポートが必要です、というメッセージを120文字程度で。ユーザーの具体的な悩み・状況と、その状況に対して石がどのようにサポートするのかを説明してください。【】見出しは絶対に使わず、自然な文章だけで書いてください。重要な言葉は**で囲んで強調。",
  "stones_for_user": [
    {{
      "name": "石の名前",
      "reason": "その石を選んだ理由（悩みとの関係を詳しく説明）"
    }}
  ],
  "element": "ユーザーに必要なエレメント (water/fire/wind/earth)",
  "theme": "テーマ (love/heal/action/intuition)"
}}
"""


def choose_main_stones(ai_stones):
    # AIの提案名から、在庫テーブルにマッチするものだけ拾う
    matched = []
    for s in ai_stones:
        name = s.get("name", "")
        for stock_name, info in STOCK_STONES.items():
            if info["role"] != "main":
                continue
            if stock_name in name:
                matched.append({"name": stock_name, **info,
                               "reason": s.get("reason", "")})
                break

    # 何もマッチしなければ、適当なメイン1個フォールバック
    if not matched:
        fallback_name = "アメジスト"
        info = STOCK_STONES[fallback_name]
        matched = [{
            "name": fallback_name,
            **info,
            "reason": "今回のテーマに合う代表的な守護石として選びました。"
        }]

    # 最大2個までに制限
    return matched[:2]


def choose_sub_stones(main_stones):
    sub_candidates = []
    for m in main_stones:
        color = m["color"]
        for sub_name in MAIN_TO_SUB_MAP.get(color, []):
            info = STOCK_STONES[sub_name]
            sub_candidates.append({
                "name": sub_name,
                **info,
                "reason": f"{m['name']}との色合いの相性を整えるために選びました。"
            })

    # 重複を削除
    uniq = {}
    for s in sub_candidates:
        uniq[s["name"]] = s
    # サブは1〜2個程度
    return list(uniq.values())[:2]


def generate_bracelet_reading(user_input: dict) -> dict:
    """ユーザー情報に基づき、オラクルカード・鑑定・石の提案を生成"""
    if not client:
        return {"error": "Perplexity API Key not configured"}

    # 1. オラクルカード抽選（石を選ぶ + 正逆を決める）
    card = random.choice(CRYSTAL_ORACLE_CARDS)
    is_upright = random.choice([True, False])  # 50%で正位置/逆位置
    meaning = card['meaning_up'] if is_upright else card['meaning_rev']

    oracle_result = {
        "card": card,
        "is_upright": is_upright,
        "meaning": meaning
    }

    # 2. AI鑑定実行
    system_msg = SYSTEM_PROMPT
    user_msg = create_user_prompt(user_input, oracle_result)
    print("=== SYSTEM PROMPT ===")
    print(system_msg)
    print("=== USER PROMPT ===")
    print(user_msg)

    try:
        resp = client.chat.completions.create(
            model="sonar-pro",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.7,
            max_tokens=3000
        )

        print("=== RESPONSE OBJECT ===")
        print(resp)

        content = resp.choices[0].message.content
        print("=== RAW CONTENT ===")
        print(content)

        # JSONクリーニング
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        # 引用表記削除
        content = re.sub(r'\[\d+\]', '', content)

        print("=== CLEANED CONTENT ===")
        print(content)

        try:
            result = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            print(f"Failed content (first 500 chars): {content[:500]}")

            # フォールバック：最低限の形だけ返す
            # ここでは、メインの石だけは決め打ちでアメジストにしておく例
            fallback = {
                "destiny_map": "",
                "past": "",
                "present": "",
                "future": "",
                "element_diagnosis": "",
                "oracle_message": "",
                "bracelet_proposal": "",
                "stone_support_message": "",
                "stones_main":[
                    {"name":"メイン石"}
                ],
                "stones_sub":[
                    {"name":"サブ石"}
                ],
                # 今後 element_lack を使うならここで決めてもOK（今は空で可）
                "element_lack": ""
            }
            result = fallback
        print("=== FINAL RESULT ===")
        print(result)

        # 3. 画像生成URL (Pollinations.ai)
        # オラクルカード画像
        card_prompt = f"oracle card art of {card['en']}, mystical glowing gemstone, divine light, intricate golden border, fantasy art, tarot style, high quality, 8k"
        card_image_url = f"https://image.pollinations.ai/prompt/{card_prompt.replace(' ', '%20')}?width=400&height=600&seed={random.randint(0, 9999)}"

        # 石候補の画像
        element = result.get("element")
        theme = result.get("theme")

        # AIの提案石から、在庫テーブルにマッチするものを選定して、メイン石とサブ石を決定するロジック
        # 1) AIの stones_for_user からメイン石を決定（1〜2個）
        main_stones = choose_main_stones(element)

        # 2) メインの色合いからサブ石（8mm）を決定
        sub_stones = choose_sub_stones(main_stones)

        # 3) クライアントに返す stones_for_user を「メイン＋サブ」に差し替え
        result["stones_for_user"] = main_stones + sub_stones

        # 必要なら、別フィールドで区別してもOK
        result["stones_main"] = main_stones
        result["stones_sub"] = sub_stones

        # 結果に統合
        # ここまでで result["stones_for_user"] = main + sub に差し替え済みとする

        # 3-A) オラクルカード情報
        result['oracle_card'] = {
            'name': card['name'],
            'meaning': meaning,
            'is_upright': is_upright,
            'image_url': card_image_url
        }

        # 3-B) 石画像プロンプトは「最終決定済みstones_for_user」から作る
        stone_names_ja = ", ".join([s["name"]
                                   for s in result["stones_for_user"]])
        stones_prompt = (
            f"gemstone bracelet design, {stone_names_ja}, crystal photography, "
            "soft lighting, white background, high quality, 8k"
        )
        bracelet_prompt = f"""
        luxury gemstone bracelet,
        {stone_names_ja},
        japanese spiritual jewelry,
        white background,
        product photography,
        high quality
        """

        result["image_prompt"] = bracelet_prompt

        result['stones_image_url'] = stones_image_url

        element = "water"  # 今は固定
        theme = choose_theme(user_input.get("concerns", []))
        gender = normalize_gender(user_input.get("gender"))

        product = choose_product(element, theme, gender)

        if product:
            result["product_name"] = product["product_name"]
            result["product_slug"] = product["product_slug"]
            return result

    except Exception as e:
        print(f"Perplexity API Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
