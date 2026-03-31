"""Perplexity AI連携モジュール

占い診断のAI鑑定、ホロスコープ計算、石の選定ロジックを提供する。
Perplexity API（OpenAI互換）を使用して、ユーザーの出生情報と悩みから
パーソナライズされた鑑定結果を生成する。
"""

import os
import json
import re
import random
import logging
import swisseph as swe
from datetime import datetime
from openai import OpenAI

logger = logging.getLogger(__name__)

# ===== API クライアント =====

PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY")


def _get_client() -> OpenAI | None:
    """Perplexity APIクライアントを取得する（遅延初期化）"""
    if not PERPLEXITY_API_KEY:
        return None
    return OpenAI(
        api_key=PERPLEXITY_API_KEY,
        base_url="https://api.perplexity.ai",
    )


# ===== 商品マッピング =====

PRODUCT_BY_MAIN_STONE = {
    "ラピスラズリ": {"id": 1203, "slug": "bracelet-lapis-gray"},
    "カーネリアン・サードニクス": {"id": 1204, "slug": "bracelet-carnelian-gray"},
    "マラカイト": {"id": 1205, "slug": "bracelet-malachite-gray"},
    "アメジスト": {"id": 1206, "slug": "bracelet-amethyst-gray"},
}

LIMITED_PRODUCTS = {
    "ラピスラズリ": {"id": 1207, "slug": "bracelet-iris-lapis-gray"},
    "カーネリアン・サードニクス": {"id": 1208, "slug": "bracelet-iris-carnelian-gray"},
    "マラカイト": {"id": 1209, "slug": "bracelet-iris-malachite-gray"},
    "アメジスト": {"id": 1210, "slug": "bracelet-iris-amethyst-gray"},
}

COLOR_PRODUCTS = {
    "マダガスカル産ローズクォーツ": {"id": 1202, "slug": "bracelet-yasashiitsuki"},
    "シーブルーカルセドニー": {"id": 1201, "slug": "bracelet-shizukanaumi"},
}

# ===== 星座・エレメント定義 =====

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

ELEMENT_MAP = {
    "Aries": "fire", "Leo": "fire", "Sagittarius": "fire",
    "Taurus": "earth", "Virgo": "earth", "Capricorn": "earth",
    "Gemini": "wind", "Libra": "wind", "Aquarius": "wind",
    "Cancer": "water", "Scorpio": "water", "Pisces": "water",
}

SIGN_JA = {
    "Aries": "牡羊座", "Taurus": "牡牛座", "Gemini": "双子座",
    "Cancer": "蟹座", "Leo": "獅子座", "Virgo": "乙女座",
    "Libra": "天秤座", "Scorpio": "蠍座", "Sagittarius": "射手座",
    "Capricorn": "山羊座", "Aquarius": "水瓶座", "Pisces": "魚座",
}

ELEMENT_JA = {
    "fire": "火", "earth": "地", "wind": "風", "water": "水",
}

# ===== オラクルカード定義 =====

CRYSTAL_ORACLE_CARDS = [
    {
        "name": "アメジスト",
        "en": "Amethyst crystal",
        "meaning_up": "精神の安定・直感の覚醒",
        "meaning_rev": "不安・逃避・考えすぎ",
    },
    {
        "name": "ラピスラズリ",
        "en": "Lapis Lazuli crystal",
        "meaning_up": "真実・洞察・精神性の成長",
        "meaning_rev": "自己不信・コミュニケーションの滞り",
    },
    {
        "name": "カーネリアン・サードニクス",
        "en": "Carnelian Sardonyx crystal",
        "meaning_up": "行動力・情熱・自己表現",
        "meaning_rev": "衝動・エネルギーの空回り",
    },
    {
        "name": "マラカイト",
        "en": "Malachite crystal",
        "meaning_up": "深い癒やし・感情の解毒",
        "meaning_rev": "感情の停滞・過去への執着",
    },
    {
        "name": "アイリスクォーツ",
        "en": "Iris Quartz crystal",
        "meaning_up": "希望・再生・波動の調整",
        "meaning_rev": "気力不足・未来への不安",
    },
]

# ===== 在庫石データ =====

STOCK_STONES = {
    "ラピスラズリ": {"size": 10, "code": "G516-6H785", "role": "main", "color": "blue"},
    "カーネリアン・サードニクス": {"size": 10, "code": "G1096-H9127", "role": "main", "color": "orange"},
    "マラカイト": {"size": 10, "code": "N294-MCT10", "role": "main", "color": "green"},
    "アイリスクォーツ": {"size": 12, "code": "N780-7283M", "role": "main", "color": "clear"},
    "アメジスト": {"size": 10, "code": "N477-8824X", "role": "main", "color": "purple"},
    "シーブルーカルセドニー": {"size": 8, "code": "CC359-01RA/#1", "role": "sub", "color": "light_blue"},
    "マダガスカル産ローズクォーツ": {"size": 8, "code": "N560-V4534", "role": "sub", "color": "pink"},
    "グレークォーツ": {"size": 10, "code": "G264-3836G", "role": "sub", "color": "gray"},
}

MAIN_TO_SUB_MAP = {
    "purple": ["マダガスカル産ローズクォーツ", "シーブルーカルセドニー", "グレークォーツ"],
    "blue": ["シーブルーカルセドニー", "グレークォーツ"],
    "orange": ["マダガスカル産ローズクォーツ", "グレークォーツ"],
    "green": ["シーブルーカルセドニー", "グレークォーツ"],
    "clear": ["マダガスカル産ローズクォーツ", "シーブルーカルセドニー", "グレークォーツ"],
    "gray": ["マダガスカル産ローズクォーツ", "シーブルーカルセドニー"],
}

SELECTABLE_STONES = "\n".join([
    "- ラピスラズリ",
    "- カーネリアン・サードニクス",
    "- マラカイト",
    "- アメジスト",
    "- アイリスクォーツ",
])

# ===== プロンプト定義 =====

SYSTEM_PROMPT = f"""
【絶対ルール】
1. 出力はすべて日本語のみ。英語は一切使用禁止。
   • 星座名: Gemini→双子座、Aries→牡羊座 のように日本語に変換
   • エレメント: fire→火、earth→地、wind→風、water→水
   • その他あらゆる英単語も日本語に置き換えてください
2. JSON形式のみを出力。Markdownのコードブロックや引用表記([1]など)は不要。
3. 【】のような見出しマークは使わず、自然な文章で書く。
4. 重要な言葉は**で囲って強調。
5. 「。」の後には改行を2つ入れる。
6. 分かりやすく、具体的で、読んだ人が「自分のことだ」と感じられる言葉で書く。
7. 神秘的・占い師的な言い回しは避け、パーソナル診断レポートとして読めるトーンにする。
   例：「運命が〜」→「あなたの傾向として〜」／「星が告げる」→「この配置から読み取れるのは」
8. 各セクションは指定文字数を目安に、現状分析と具体的なアドバイスをバランスよく。

【重要なルール】
選べる天然石は必ず以下のいずれか1つにしてください。
それ以外の石（例：水晶、クリスタル等）は絶対に選ばないでください。
"""


# ===== ホロスコープ計算 =====

# Swiss Ephemeris のデータパス設定
# swe.set_ephe_path(None) はビルトインのMoshier ephemerisを使用する。
# Moshier ephemerisは外部データファイル不要で、Vercelサーバーレス環境でも動作する。
# 精度はSwiss Ephemeris本体（約0.001秒角）より劣るが、
# 占星術の実用上十分な精度（約0.1秒角）を持つ。
swe.set_ephe_path(None)


def calculate_chart(date: str, time: str, lat: float, lon: float) -> dict:
    """出生情報から惑星の黄経を計算し、星座とエレメントバランスを返す

    Swiss Ephemeris（pyswisseph）を使用してホロスコープチャートを計算する。
    Swiss Ephemerisは天文学的に正確な惑星位置計算ライブラリで、
    指定された日時・場所から各惑星の黄道上の位置（黄経）を算出する。

    ビルトインのMoshier ephemerisを使用するため、外部データファイルは不要。

    Args:
        date: 生年月日（"YYYY-MM-DD"形式）
        time: 出生時間（"HH:MM"形式）
        lat: 出生地の緯度
        lon: 出生地の経度

    Returns:
        星座配置とエレメントバランスを含む辞書
    """
    try:
        dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    except ValueError:
        logger.warning(f"日時パースエラー: date={date}, time={time}")
        return {}

    # ユリウス日の計算（天文計算の基準日時）
    jd = swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute / 60.0)

    planets = {
        "sun": swe.SUN,
        "moon": swe.MOON,
        "mercury": swe.MERCURY,
        "venus": swe.VENUS,
        "mars": swe.MARS,
    }

    # 各惑星の黄経を計算し、星座を判定
    positions = {}
    signs = {}
    for name, planet_id in planets.items():
        try:
            result = swe.calc_ut(jd, planet_id)
            longitude = result[0][0]  # 黄経（度）
            positions[name] = longitude
            signs[name] = get_sign(longitude)
        except Exception as e:
            logger.warning(f"惑星計算エラー ({name}): {e}")
            signs[name] = _DEFAULT_CHART.get(name, "Aries")

    # ASC（アセンダント）の計算
    try:
        houses = swe.houses(jd, lat, lon, b'P')  # Placidusハウスシステム
        asc_degree = houses[1][0]  # ASCの黄経
        asc_sign = get_sign(asc_degree)
    except Exception as e:
        logger.warning(f"ASC計算エラー: {e}")
        asc_sign = _DEFAULT_CHART.get("asc", "Cancer")

    # エレメントバランスの計算
    all_signs = {**signs, "asc": asc_sign}
    balance = sign_element_balance(all_signs)

    return {
        "sun": signs.get("sun", "Aries"),
        "moon": signs.get("moon", "Aries"),
        "mercury": signs.get("mercury", "Aries"),
        "venus": signs.get("venus", "Aries"),
        "mars": signs.get("mars", "Aries"),
        "asc": asc_sign,
        "element_balance": balance,
    }


def get_sign(deg: float) -> str:
    """黄経（度数）から星座名を返す"""
    return SIGNS[int(deg / 30) % 12]


def sign_element_balance(signs: dict) -> dict:
    """星座配分から4エレメントのバランスを算出する"""
    count = {"fire": 0, "earth": 0, "wind": 0, "water": 0}
    for s in signs.values():
        if s in ELEMENT_MAP:
            count[ELEMENT_MAP[s]] += 1
    return count


def weakest_element(balance: dict) -> str:
    """最も弱いエレメントを返す"""
    return min(balance, key=balance.get)


# ===== チャートデータ構築 =====

# デフォルトのチャートデータ（出生情報が不明な場合のフォールバック）
_DEFAULT_CHART = {
    "sun": "Gemini", "moon": "Pisces", "asc": "Cancer",
    "mercury": "Taurus", "venus": "Cancer", "mars": "Leo",
    "element_balance": {"fire": 1, "earth": 1, "wind": 2, "water": 2},
}


def build_chart_data(user_input: dict = None, chart_data: dict = None) -> dict:
    """ホロスコープチャートデータを構築する

    実際のチャート計算結果があればそれを使い、なければデフォルト値で補完する。
    """
    base = chart_data or {
        "sun": _DEFAULT_CHART["sun"],
        "moon": _DEFAULT_CHART["moon"],
        "asc": _DEFAULT_CHART["asc"],
        "mercury": _DEFAULT_CHART["mercury"],
        "venus": _DEFAULT_CHART["venus"],
        "mars": _DEFAULT_CHART["mars"],
        "element_balance": _DEFAULT_CHART.get("element_balance", {}),
    }

    balance = base.get("element_balance", {})
    fire = balance.get("fire", 1)
    earth = balance.get("earth", 1)
    wind = balance.get("wind", 1)
    water = balance.get("water", 1)

    element_lack = base.get("element_lack")
    if not element_lack:
        element_lack = weakest_element({
            "fire": fire, "earth": earth, "wind": wind, "water": water,
        })

    sun = base.get("sun", "Gemini")
    moon = base.get("moon", "Pisces")
    asc = base.get("asc", "Cancer")
    mercury = base.get("mercury", "Taurus")
    venus = base.get("venus", "Cancer")
    mars = base.get("mars", "Leo")

    return {
        "sun": sun, "moon": moon, "asc": asc,
        "mercury": mercury, "venus": venus, "mars": mars,
        "fire": fire, "earth": earth, "wind": wind, "water": water,
        "element_lack": element_lack,
        "sun_ja": SIGN_JA.get(sun, sun),
        "moon_ja": SIGN_JA.get(moon, moon),
        "asc_ja": SIGN_JA.get(asc, asc),
        "mercury_ja": SIGN_JA.get(mercury, mercury),
        "venus_ja": SIGN_JA.get(venus, venus),
        "mars_ja": SIGN_JA.get(mars, mars),
        "element_lack_ja": ELEMENT_JA.get(element_lack, element_lack),
    }


# ===== 商品選定 =====

def choose_products(main_stone: str, sub_stones: list) -> list:
    """メイン石とサブ石から購入候補の商品リストを生成する"""
    products = []

    base = PRODUCT_BY_MAIN_STONE.get(main_stone)
    if base:
        products.append(base)

    # サブ石にグレークォーツがあればアイリスシリーズも追加
    has_gray = any(s["name"] == "グレークォーツ" for s in sub_stones)
    if has_gray:
        limited = LIMITED_PRODUCTS.get(main_stone)
        if limited:
            products.append(limited)

    # サブ石にローズ or シーブルーがあれば色系商品も追加
    for s in sub_stones:
        color_prod = COLOR_PRODUCTS.get(s["name"])
        if color_prod and color_prod not in products:
            products.append(color_prod)

    return products


# ===== テーマ選定 =====

def choose_theme(concerns: list) -> str:
    """悩みカテゴリからテーマを決定する"""
    if not concerns:
        return "heal"

    concern_theme_map = {
        "恋愛": "love",
        "仕事": "action",
        "金運": "action",
        "健康": "heal",
        "人間関係": "intuition",
    }

    for concern, theme in concern_theme_map.items():
        if concern in concerns:
            return theme

    return "heal"


# ===== 石選定 =====

def choose_main_stones(ai_stones: list) -> list:
    """AIが選んだ石を在庫データと照合し、メイン石リストを返す"""
    matched = []
    for s in ai_stones:
        name = s.get("name", "")
        if name in STOCK_STONES and STOCK_STONES[name]["role"] == "main":
            matched.append({
                "name": name,
                **STOCK_STONES[name],
                "reason": s.get("reason", ""),
            })

    if not matched:
        fallback_name = "ラピスラズリ"
        info = STOCK_STONES[fallback_name]
        matched = [{
            "name": fallback_name,
            **info,
            "reason": "運命と真実を導く守護石としてラピスラズリが選ばれました。",
        }]

    return matched[:2]


def choose_sub_stones(main_stones: list) -> list:
    """メイン石の色相性に基づいてサブ石を選定する"""
    seen = {}
    for m in main_stones:
        color = m.get("color", "")
        for sub_name in MAIN_TO_SUB_MAP.get(color, []):
            if sub_name not in seen:
                info = STOCK_STONES[sub_name]
                seen[sub_name] = {
                    "name": sub_name,
                    **info,
                    "reason": f"{m['name']}との色合いの相性を整えるために選びました。",
                }

    return list(seen.values())[:2]


# ===== AIレスポンスのパース =====

def _strip_code_block(content: str) -> str:
    """AIレスポンスからMarkdownコードブロックを除去する"""
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    return content


def _clean_citations(content: str) -> str:
    """引用表記 [1] [2] などを除去する"""
    return re.sub(r"\[\d+\]", "", content)


# ===== プロンプト構築 =====

def build_common_user_context(
    user_input: dict, chart_data: dict = None, oracle_result: dict = None
) -> str:
    """共通のユーザー情報コンテキストを構築する"""
    birth = user_input.get("birth", {})
    concerns = user_input.get("concerns", [])
    problem_text = user_input.get("problem", "")
    concerns_text = "、".join(concerns) if concerns else "指定なし"

    cd = build_chart_data(user_input, chart_data)

    oracle_text = ""
    if oracle_result:
        position_str = "正位置" if oracle_result["is_upright"] else "逆位置"
        oracle_text = (
            f"\n\n【オラクルカード結果】\n"
            f"カード: {oracle_result['card']['name']}\n"
            f"状態: {position_str}\n"
            f"意味: {oracle_result['meaning']}"
        )

    return f"""
【ユーザー情報】
性別: {user_input.get('gender', '指定なし')}
悩みカテゴリ: {concerns_text}

具体的な悩み:
{problem_text if problem_text else '指定なし'}

生年月日: {birth.get('date', '不明')}
出生時間: {birth.get('time', '不明')}
出生地: {birth.get('place', '不明')}

【石の候補】
{SELECTABLE_STONES}

※水晶は特別な石です。
人生の転換期や強い浄化が必要な場合のみ選択してください。

【ホロスコープ分析】
太陽星座: {cd['sun_ja']}
月星座: {cd['moon_ja']}
アセンダント（上昇宮）: {cd['asc_ja']}
水星: {cd['mercury_ja']}
金星: {cd['venus_ja']}
火星: {cd['mars_ja']}

エレメントバランス
火:{cd['fire']}  地:{cd['earth']}  風:{cd['wind']}  水:{cd['water']}

不足エレメント: {cd['element_lack_ja']}
{oracle_text}
"""


def create_today_fortune_prompt(user_input: dict, chart_data: dict = None) -> str:
    """今日の運勢用プロンプトを構築する"""
    common_context = build_common_user_context(
        user_input=user_input,
        chart_data=chart_data,
        oracle_result=None,
    )

    return f"""
以下の情報をもとに、今日一日のエネルギー傾向と過ごし方のヒントを日本語で1メッセージだけ生成してください。

あなたは、西洋占星術と天然石の特性に詳しいパーソナルアドバイザーです。
神秘的・占い的な表現は避け、「今のあなたの状態」を分かりやすく分析するように伝えてください。

{common_context}

【出力条件】
- メッセージ本文だけを返してください
- JSON不要、コードブロック不要
- 3段落で構成
- 各段落は3〜5行以内
- 今日の傾向、行動のコツ、気持ちの整え方を含める
- 「今日のあなたは…」のような自然な導入を含める
- 前向きで具体的な内容にする
"""


def create_user_prompt(
    user_input: dict, oracle_result: dict, chart_data: dict = None
) -> str:
    """メイン診断用のユーザープロンプトを構築する"""
    common_context = build_common_user_context(
        user_input=user_input,
        chart_data=chart_data,
        oracle_result=oracle_result,
    )

    position_str = "正位置" if oracle_result["is_upright"] else "逆位置"

    concerns = user_input.get("concerns", [])
    concerns_text = "、".join(concerns) if concerns else "全体運"
    problem_text = (user_input.get("problem") or "").strip()

    # ユーザーが具体的な悩みを書いている場合は、それを最優先で扱う
    problem_instruction = ""
    if problem_text:
        problem_instruction = f"""
【最重要】ユーザーが自分の言葉で書いた悩み:
「{problem_text}」

この一文一文に込められた感情・状況・言葉を最大限くみ取ってください。
すべてのセクションで、この悩みに直接応えるように語りかけること。
ホロスコープはこの悩みを読み解くための「補足」として使い、
あくまでユーザーの悩みが鑑定の中心軸です。
"""
    else:
        problem_instruction = f"今回のユーザーの悩みカテゴリは「{concerns_text}」です。すべてのセクションで、この悩みに沿った場面や感情を交えてください。"

    return f"""
以下の情報をもとに、パーソナル診断レポートを作成してください。

あなたは西洋占星術と天然石の特性に詳しいパーソナルアドバイザーです。
神秘的・占い的な表現は使わず、読んだ人が「自分の傾向が分かった」と感じられる
具体的で分かりやすい言葉で書いてください。

{problem_instruction}

{common_context}

【文体のルール】
- 占術用語・英語略語は使わない（「トランジット」「ハウス」「アセンダント」「MC」「IC」など禁止）
- 「運命」「宿命」「星が示す」などのスピリチュアル表現は避ける
- 「〜な傾向があります」「〜しやすい時期です」など分析・診断的な言い回しを使う
- ユーザーの悩みに出てくる具体的な言葉・場面・感情をそのまま拾って使う
- 1文を短くし、読んでいて息苦しくない長さにする
- 「〜です。\n\n」のように句点後は改行を2つ入れる

【出力JSONスキーマ】
{{
"destiny_map": "ホロスコープ配置から読み取れる、生まれ持った気質と今後向いている方向性を250文字程度で。「あなたの星座バランスから見えてくるのは、〜という傾向です」のように分析口調で始める。ユーザーの悩みとの関連を含める。",
"past": "これまでのユーザーの行動パターンや強みを150文字程度で。「これまでのあなたは〜という特性を持っています」のように特性を整理する。ユーザーの悩みに関連する強みを含める。",
"present_future": "今の状態と、これからの変化の方向性を200文字程度で。「いまのあなたは〜という状態にあります」と現状を整理し、「〜を意識することで」と具体的な行動につながるヒントを伝える。ユーザーの悩みに直接沿って書く。",
"element_diagnosis": "星座バランスから分かるエネルギーの偏りを150文字程度で。「最近、〇〇な気持ちになることはありませんか？」と問いかけてから、バランスの特徴を説明する。ユーザーの悩みに絡めた具体例を1つ入れる。",
"oracle_message": "引いたカード「{oracle_result['card']['name']}」の{position_str}が示すヒントを150文字程度で。「このカードが示すのは〜ということです」と、今のあなたへの示唆として伝える。ユーザーの悩みへの気づきにつなげる。",
"bracelet_proposal": "この石を日常に取り入れることで期待できる変化を150文字程度で。ユーザーの悩みに関連する具体的な場面（例：「〜で困っているとき、この石を身につけることで」）を描く。",
"stone_support_message": "選ばれた石の特性がユーザーの現状にどう作用するかを200文字程度で。「この石の特性は〜で、あなたの〜という状況に対して」と、石の性質と現状のマッチングを具体的に説明する。",
"daily_advice": "今日からできる具体的なアクションを3つ、それぞれ25文字以内で。カンマ区切り。ユーザーの悩みに関連する実践的な行動を含める。",
"lucky_color": "今日意識するとよいカラー（1色、日本語）",
"affirmation": "自己肯定のひと言を50文字程度で。「私は…」で始める。ユーザーの悩みに関連した前向きな言葉にする。",
"chosen_stone": {{
  "name": "選ばれた石の名前（日本語）",
  "reason": "ユーザーの悩み・星座バランス・カードの観点からその石が適している理由を1〜2文で。悩みへの言及を必ず含める。"
}},
"element": "ユーザーに必要なエレメント（火/地/風/水）",
"theme": "テーマ（恋愛/癒し/行動/直感）"
}}

必ずJSON形式のみで出力。JSON以外のテキストや説明は一切不要。
英語が一文字でも含まれていたらやり直し。
"""


# ===== 今日の運勢生成 =====

def generate_today_fortune(user_input: dict, chart_data: dict = None) -> str:
    """今日の運勢テキストを生成する

    APIが利用できない場合はフォールバックメッセージを返す。
    """
    client = _get_client()
    if not client:
        return "今日は、自分のペースを大切に過ごすと良さそうな日です。"

    system_prompt = (
        "あなたは、西洋占星術と天然石の特性に詳しいパーソナルアドバイザーです。\n"
        "生年月日・出生時間・出生地・ホロスコープ情報をもとに、\n"
        "今日のエネルギー傾向を分かりやすく分析してください。\n"
        "神秘的・占い師的な表現は避け、診断レポートのようなトーンで伝えてください。\n"
    ) + SYSTEM_PROMPT

    user_prompt = create_today_fortune_prompt(user_input, chart_data)

    try:
        resp = client.chat.completions.create(
            model="sonar-pro",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=500,
        )

        content = resp.choices[0].message.content.strip()
        content = _strip_code_block(content)
        content = _clean_citations(content)
        return content

    except Exception as e:
        logger.exception("今日の運勢生成でエラー")
        return "今日は、自分のペースを大切に過ごすと良さそうな日です。"


# ===== メイン診断生成 =====

def generate_bracelet_reading(user_input: dict, chart_data: dict = None) -> dict:
    """AIを使ったブレスレット診断を実行する

    オラクルカードをランダムに引き、ユーザーの情報と合わせて
    AIに鑑定を依頼し、石の選定まで行う。
    """
    client = _get_client()
    if not client:
        return {"error": "鑑定APIの設定が完了していません"}

    # オラクルカードを引く
    card = random.choice(CRYSTAL_ORACLE_CARDS)
    is_upright = random.choice([True, False])
    meaning = card["meaning_up"] if is_upright else card["meaning_rev"]

    oracle_result = {
        "card": card,
        "is_upright": is_upright,
        "meaning": meaning,
    }

    system_msg = (
        "あなたは、西洋占星術と天然石の特性に詳しいパーソナルアドバイザーです。\n"
        "ユーザーの悩みを起点に、ホロスコープで傾向を分析し、最適な石を提案してください。\n\n"
        "【最重要ルール】\n"
        "ユーザーが自分の言葉で書いた「具体的な悩み」が診断の中心です。\n"
        "ホロスコープや星座はその悩みを読み解くための補足情報として使い、\n"
        "すべてのセクションでユーザーの悩みに具体的に応えてください。\n"
        "神秘的・占い師的な表現は避け、「〜という傾向があります」「〜しやすい状態です」など\n"
        "分かりやすい診断・アドバイスの言葉で伝えてください。\n\n"
        "【前提条件】\n"
        "- ユーザーの「悩み詳細」を最優先で読み取り、具体的に応えること。\n"
        "- この段階ではブレスレットの個数・配置は決めず、「最適な石の種類」だけを提案します。\n"
        "- destiny_map では、出生時間・出生地の情報があれば星座バランスの分析に活かしてください。\n\n"
        f"【石の候補】\n{SELECTABLE_STONES}\n\n"
        "※水晶は特別な石です。\n"
        "人生の転換期や強い浄化が必要な場合のみ選択してください。\n"
    ) + SYSTEM_PROMPT

    user_msg = create_user_prompt(user_input, oracle_result, chart_data)

    try:
        resp = client.chat.completions.create(
            model="sonar-pro",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.7,
            max_tokens=3000,
        )

        content = resp.choices[0].message.content.strip()
        content = _strip_code_block(content)
        content = _clean_citations(content)

        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            logger.warning(f"AIレスポンスのJSONパースに失敗: {content[:200]}")
            result = {}

        if not isinstance(result, dict):
            result = {"destiny_map": str(result)}

        # デフォルト値の設定
        result.setdefault("destiny_map", "")
        result.setdefault("past", "")
        result.setdefault("present_future", "")
        result.setdefault("element_diagnosis", "")
        result.setdefault("oracle_message", "")
        result.setdefault("bracelet_proposal", "")
        result.setdefault("stone_support_message", "")
        result.setdefault("element", "water")
        result.setdefault("theme", choose_theme(user_input.get("concerns", [])))

        # 選ばれた石の処理
        chosen_stone = result.get("chosen_stone") or {}
        chosen_name = chosen_stone.get("name", "ラピスラズリ")
        chosen_reason = chosen_stone.get(
            "reason",
            f"あなたの運命を導く守護石として{chosen_name}が選ばれました。",
        )

        ai_stones = [{"name": chosen_name, "reason": chosen_reason}]

        main_stones = choose_main_stones(ai_stones)
        sub_stones = choose_sub_stones(main_stones)

        result["stones_for_user"] = main_stones + sub_stones
        result["stones_main"] = main_stones
        result["stones_sub"] = sub_stones

        # エレメント情報
        chart_info = build_chart_data(user_input, chart_data)
        result["element_lack"] = chart_info["element_lack"]

        # オラクルカード情報と画像生成
        from concurrent.futures import ThreadPoolExecutor
        from api.utils_image import (
            get_stone_colors,
            generate_oracle_card_image,
            generate_destiny_scene,
            generate_element_balance,
            generate_stone_beads_image,
        )

        chart_info_for_img = build_chart_data(user_input, chart_data)
        main_stone_name = result["stones_main"][0]["name"]
        sub_stone_names = [s["name"] for s in result.get("stones_sub", [])]

        result["stone_colors"] = get_stone_colors(main_stone_name)

        # キャッシュキーは内容ベース（同じ石・エレメント・カードなら別ユーザーでもキャッシュ共有）
        # 誕生日など個人情報はキーに含めない
        position_key = "up" if is_upright else "rev"
        element_key  = f"{chart_info_for_img['element_lack_ja']}-{main_stone_name}"
        balance_key  = f"{chart_info_for_img['fire']}-{chart_info_for_img['earth']}-{chart_info_for_img['wind']}-{chart_info_for_img['water']}"
        beads_key    = "-".join(sorted([main_stone_name] + sub_stone_names))

        # 4枚の画像を並列生成
        with ThreadPoolExecutor(max_workers=4) as executor:
            f_oracle = executor.submit(
                generate_oracle_card_image,
                card["name"], card["en"], is_upright,
                f"oracle-{card['name']}-{position_key}",   # カード名+正逆のみ
            )
            f_destiny = executor.submit(
                generate_destiny_scene,
                chart_info_for_img["element_lack_ja"],
                main_stone_name,
                f"destiny-{element_key}",                   # エレメント+石名のみ
                result.get("destiny_map", ""),
            )
            f_element = executor.submit(
                generate_element_balance,
                chart_info_for_img["fire"],
                chart_info_for_img["earth"],
                chart_info_for_img["wind"],
                chart_info_for_img["water"],
                f"element-{balance_key}",                   # バランス数値のみ
                result.get("element_diagnosis", ""),
            )
            f_beads = executor.submit(
                generate_stone_beads_image,
                main_stone_name,
                sub_stone_names,
                f"beads-{beads_key}",                       # 石名の組み合わせのみ
            )
            oracle_image  = f_oracle.result()
            destiny_image = f_destiny.result()
            element_image = f_element.result()
            beads_image   = f_beads.result()

        result["oracle_card"] = {
            "name": card["name"],
            "meaning": meaning,
            "is_upright": is_upright,
            "colors": get_stone_colors(card["name"]),
            "image_url": oracle_image,
        }

        result["images"] = {
            "destiny_scene":   destiny_image,
            "element_balance": element_image,
            "beads":           beads_image,
        }

        # 商品候補
        main = result["stones_main"][0]["name"]
        result["products"] = choose_products(main, result["stones_sub"])

        return result

    except Exception as e:
        logger.exception("Perplexity API エラー")
        return {"error": str(e)}
