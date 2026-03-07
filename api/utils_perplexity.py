import os
import json
import re
import random
from openai import OpenAI


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
CRYSTAL_ORACLE_CARDS = [
    {
        "name": "アメジスト", "en": "Amethyst crystal",
        "meaning_up": "精神の安定・直感の覚醒", "meaning_rev": "不安・逃避・考えすぎ"
    },
    {
        "name": "ローズクォーツ", "en": "Rose Quartz crystal",
        "meaning_up": "無条件の愛・自己受容", "meaning_rev": "自信喪失・愛への渇望"
    },
    {
        "name": "シトリン", "en": "Citrine crystal",
        "meaning_up": "繁栄・自信・成功", "meaning_rev": "散財・エネルギー不足"
    },
    {
        "name": "クリアクォーツ", "en": "Clear Quartz crystal",
        "meaning_up": "浄化・新しいスタート", "meaning_rev": "混乱・方向性の喪失"
    },
    {
        "name": "ブラックトルマリン", "en": "Black Tourmaline crystal",
        "meaning_up": "強力な保護・グラウンディング", "meaning_rev": "恐れ・ネガティブな思考"
    },
    {
        "name": "ラピスラズリ", "en": "Lapis Lazuli crystal",
        "meaning_up": "真実・第三の目", "meaning_rev": "コミュニケーション不足・幻想"
    },
    {
        "name": "カーネリアン", "en": "Carnelian crystal",
        "meaning_up": "行動力・情熱", "meaning_rev": "怒り・無気力"
    },
    {
        "name": "ムーンストーン", "en": "Moonstone crystal",
        "meaning_up": "女性性・神秘・予感", "meaning_rev": "感情の不安定・迷い"
    }
]


SYSTEM_PROMPT = """
あなたは、西洋占星術とクリスタルヒーリングに精通したプロの占い師です。
ユーザーの悩みに寄り添い、希望を与え、まずは「相性の良い石の種類」を提案してください。

【出力形式の絶対ルール】
1. JSON形式のみを出力すること。Markdownのコードブロックは不要。
2. 引用表記（[1]など）は削除すること。
3. ユーザーの「悩み詳細」を深く読み取り、共感のこもった鑑定を行うこと。
4. この段階ではブレスレットの個数・配置は決めず、「あなたにマッチする石」だけを提案します。
5. 各セクションは指定文字数を目安に、過不足なく簡潔に書いてください。
6. 【】のような見出しマークは一切使わず、自然な文章だけで書いてください。重要な箇所は**で囲って強調してください。
7. destiny_map では、可能であれば出生時間・出生地も活かして、
   「生まれた時間帯（早朝・昼・夕方・深夜など）」や
   「生まれた土地のイメージ（海沿いの街、雪の多い地域など）」から感じられる
   人生の舞台設定や雰囲気についても1段落程度で触れてください。
   占星術用語を使いすぎず、一般の人に分かりやすい言葉でやさしく表現してください。
"""


AVAILABLE_STONES = """
- アメジスト（紫）
- ローズクォーツ（ピンク）
- シトリン（黄）
- 水晶（透明）
- オニキス（黒）
- アクアマリン（水色）
- ラピスラズリ（紺）
- タイガーアイ（茶金）
- ムーンストーン（白）
- カーネリアン（赤）
"""

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
"""

    user_prompt = f"""
以下の情報から、今日一日の運勢と過ごし方のヒントを日本語で1メッセージだけ生成してください。

[ユーザー情報]
- 性別: {gender}
- 生年月日: {birth.get('date', '不明')}
- 出生時間: {birth.get('time', '不明')}
- 出生地: {birth.get('place', '不明')}

[出力条件]
- 1段落の目安は150文字前後。5段落で構成してください。
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
  "destiny_map": "全体のテーマ・運命の地図を200文字程度で。【】見出しは絶対に使わず、自然な文章だけで書いてください。重要な言葉は**で囲んで強調。",
  "past": "生まれ持った資質・これまでの流れを150文字程度で。【】見出しは絶対に使わず、自然な文章だけで書いてください。重要な言葉は**で囲んで強調。",
  "present": "今の課題・テーマを150文字程度で。【】見出しは絶対に使わず、自然な文章だけで書いてください。重要な言葉は**で囲んで強調。",
  "future": "これから開いていく可能性を150文字程度で。【】見出しは絶対に使わず、自然な文章だけで書いてください。重要な言葉は**で囲んで強調。",
  "element_diagnosis": "火・地・風・水のバランスと不足要素、アドバイスを150文字程度で。【】見出しは絶対に使わず、自然な文章だけで書いてください。重要な言葉は**で囲んで強調。",
  "oracle_message": "引いたカード「{oracle_result['card']['name']}」の{position_str}の詳細メッセージを150文字程度で。【】見出しは絶対に使わず、自然な文章だけで書いてください。重要な言葉は**で囲んで強調。",
  "bracelet_proposal": "どんな意図で石を選び、どんな願いをサポートするか、150文字程度で。【】見出しは絶対に使わず、自然な文章だけで書いてください。重要な言葉は**で囲んで強調。",
  "stone_support_message": "あなたはこういう状況であなたにはこういう石の魔法のサポートが必要です、というメッセージを200文字程度で。ユーザーの具体的な悩み・状況と、その状況に対して石がどのようにサポートするのかを説明してください。【】見出しは絶対に使わず、自然な文章だけで書いてください。重要な言葉は**で囲んで強調。",
  "stones_for_user": [
    {{
      "name": "石の名前",
      "reason": "その石を選んだ理由（悩みとの関係を詳しく説明）"
    }}
  ]
}}
"""


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
                "stones_for_user": [
                    {
                        "name": f"{card['name']}（紫）" if card["name"] == "アメジスト" else card["name"],
                        "reason": "AI応答の解析に失敗したため、オラクルカードで選ばれた石を代表石として設定しました。"
                    }
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
        card_image_url = f"https://image.pollinations.ai/prompt/{card_prompt.replace(' ', '%20')}?width=400&height=600&seed={random.randint(0,9999)}"

        # 石候補の画像
        stone_names_en = ", ".join([s['name'] for s in result.get('stones_for_user', [])])
        stones_prompt = f"gemstone collection, {stone_names_en}, crystal photography, soft lighting, white background, high quality, 8k"
        stones_image_url = f"https://image.pollinations.ai/prompt/{stones_prompt.replace(' ', '%20')}?width=600&height=400&seed={random.randint(0,9999)}"

        # 結果に統合
        result['oracle_card'] = {
            'name': card['name'],
            'meaning': meaning,
            'is_upright': is_upright,
            'image_url': card_image_url
        }

        result['stones_image_url'] = stones_image_url
        result['phase'] = 'stones_only'  # フロント側で判別用

        return result

    except Exception as e:
        print(f"Perplexity API Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}