"""画像生成・キャッシュモジュール

診断結果に合わせたイメージ画像を生成し、Google Sheetsに保存して再利用する。
Pollinations.ai の無料画像生成APIを使用。
"""

import hashlib
import logging
import random
from urllib.parse import quote

logger = logging.getLogger(__name__)


def _build_seed(key: str) -> int:
    """キーから固定のシード値を生成する（同じキーなら同じ画像）"""
    return int(hashlib.md5(key.encode()).hexdigest()[:8], 16) % 100000


def generate_oracle_card_url(card_name_en: str, seed_key: str = "") -> str:
    """オラクルカード画像のURLを生成する

    Args:
        card_name_en: カードの英語名（プロンプト用）
        seed_key: 固定シード生成用キー（空ならランダム）

    Returns:
        画像URL
    """
    seed = _build_seed(seed_key) if seed_key else random.randint(0, 99999)

    prompt = (
        f"oracle card art of {card_name_en}, "
        "mystical glowing gemstone on dark velvet background, "
        "sacred geometry, divine golden light rays, "
        "ornate art nouveau golden border frame, "
        "fantasy illustration, tarot card style, "
        "ethereal atmosphere, ultra detailed, 8k quality"
    )

    return (
        "https://image.pollinations.ai/prompt/"
        + quote(prompt, safe='')
        + f"?width=400&height=600&seed={seed}&nologo=true"
    )


def generate_destiny_scene_url(
    sun_sign_ja: str,
    moon_sign_ja: str,
    element_lack_ja: str,
    stone_name: str,
    concerns: list[str] | None = None,
    seed_key: str = "",
) -> str:
    """運命の地図シーン画像のURLを生成する

    ユーザーの星座配置に合わせた幻想的な風景画像。

    Args:
        sun_sign_ja: 太陽星座（日本語）
        moon_sign_ja: 月星座（日本語）
        element_lack_ja: 不足エレメント（日本語）
        stone_name: メイン石の名前
        concerns: 悩みカテゴリ
        seed_key: 固定シード生成用キー

    Returns:
        画像URL
    """
    seed = _build_seed(seed_key) if seed_key else random.randint(0, 99999)

    # エレメントに合わせた風景モチーフ
    element_scene = {
        "火": "volcanic landscape with warm aurora, golden flames dancing in twilight sky",
        "地": "ancient forest with crystal cave, moss covered stones and earth energy",
        "風": "floating sky islands with swirling clouds, ethereal wind currents and starlight",
        "水": "mystical underwater temple with bioluminescent coral, moonlit ocean surface",
    }

    scene = element_scene.get(element_lack_ja, "mystical starry landscape with cosmic energy")

    # 石のカラーを反映
    stone_color = {
        "ラピスラズリ": "deep royal blue and gold",
        "カーネリアン・サードニクス": "warm orange and amber",
        "マラカイト": "vivid emerald green swirls",
        "アメジスト": "deep purple and violet light",
        "アイリスクォーツ": "rainbow prismatic light through clear crystal",
    }

    color = stone_color.get(stone_name, "mystical gemstone glow")

    prompt = (
        f"{scene}, "
        f"{color} gemstone energy emanating from center, "
        "fantasy art, ethereal atmosphere, "
        "cosmic spiritual landscape, constellation patterns, "
        "no text, no people, dreamlike, "
        "digital painting, artstation quality, ultra detailed"
    )

    return (
        "https://image.pollinations.ai/prompt/"
        + quote(prompt, safe='')
        + f"?width=600&height=400&seed={seed}&nologo=true"
    )


def generate_element_balance_url(
    fire: int, earth: int, wind: int, water: int,
    seed_key: str = "",
) -> str:
    """エレメントバランス画像のURLを生成する

    4元素のバランスを視覚化する抽象画。

    Returns:
        画像URL
    """
    seed = _build_seed(seed_key) if seed_key else random.randint(0, 99999)

    # 最も強いエレメントを強調
    dominant = max(
        [("fire", fire), ("earth", earth), ("wind", wind), ("water", water)],
        key=lambda x: x[1]
    )[0]

    dominant_mood = {
        "fire": "fiery red and gold energy dominant, passionate swirling flames",
        "earth": "earthy brown and green energy dominant, crystal formations growing",
        "wind": "airy silver and white energy dominant, swirling wind currents",
        "water": "oceanic blue and teal energy dominant, flowing water streams",
    }

    prompt = (
        "four elements balance visualization, "
        "fire earth wind water energy orbs floating in cosmic space, "
        f"{dominant_mood.get(dominant, 'balanced cosmic energy')}, "
        "sacred geometry mandala background, "
        "abstract spiritual art, glowing particles, "
        "no text, symmetrical composition, "
        "digital art, ethereal, 8k quality"
    )

    return (
        "https://image.pollinations.ai/prompt/"
        + quote(prompt, safe='')
        + f"?width=600&height=400&seed={seed}&nologo=true"
    )


def generate_stone_bracelet_url(
    main_stone: str,
    sub_stones: list[str] | None = None,
    seed_key: str = "",
) -> str:
    """ブレスレット提案画像のURLを生成する

    Returns:
        画像URL
    """
    seed = _build_seed(seed_key) if seed_key else random.randint(0, 99999)

    stones_text = main_stone
    if sub_stones:
        stones_text += " with " + " and ".join(sub_stones)

    prompt = (
        f"luxury handcrafted gemstone bracelet featuring {stones_text} beads, "
        "elegant Japanese spiritual jewelry, "
        "soft studio lighting on white silk fabric, "
        "close-up product photography, "
        "bokeh background with warm light, "
        "high-end jewelry catalog style, ultra detailed, 8k"
    )

    return (
        "https://image.pollinations.ai/prompt/"
        + quote(prompt, safe='')
        + f"?width=600&height=400&seed={seed}&nologo=true"
    )
