"""画像生成モジュール

Gemini API（gemini-3.1-flash-image-preview）を使って診断結果に合わせた
イメージ画像を生成する。生成した画像はbase64エンコードでフロントエンドに返す。
同じシードキーに基づくキャッシュで再生成を防止する。

環境変数:
    GEMINI_API_KEY: Google AI Studio / Gemini APIのAPIキー
"""

import os
import json
import base64
import hashlib
import logging
import requests
import time

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-3.1-flash-image-preview"
GEMINI_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

# インメモリキャッシュ（同一プロセス内で再利用）
_image_cache: dict[str, str] = {}
CACHE_MAX_SIZE = 20  # メモリ節約のため最大20枚

# ファイルキャッシュ（/tmp はVercelの同一コンテナ内で永続、ローカルは .image_cache）
_FILE_CACHE_DIR = os.path.join(os.environ.get("TMPDIR", "/tmp"), "atlas_img_cache")
try:
    os.makedirs(_FILE_CACHE_DIR, exist_ok=True)
except Exception:
    _FILE_CACHE_DIR = ""  # ファイルキャッシュが使えない場合はスキップ


# 石ごとのカラーテーマ（CSSフォールバック用）
STONE_COLORS = {
    "ラピスラズリ": {"primary": "#1a237e", "secondary": "#5c6bc0", "accent": "#ffd54f", "gradient": "linear-gradient(135deg, #0d1b4a 0%, #1a237e 40%, #5c6bc0 100%)"},
    "カーネリアン・サードニクス": {"primary": "#bf360c", "secondary": "#ff6e40", "accent": "#ffd180", "gradient": "linear-gradient(135deg, #4a1a0a 0%, #bf360c 40%, #ff6e40 100%)"},
    "マラカイト": {"primary": "#1b5e20", "secondary": "#66bb6a", "accent": "#c8e6c9", "gradient": "linear-gradient(135deg, #0a2e0f 0%, #1b5e20 40%, #66bb6a 100%)"},
    "アメジスト": {"primary": "#4a148c", "secondary": "#ab47bc", "accent": "#e1bee7", "gradient": "linear-gradient(135deg, #1a0533 0%, #4a148c 40%, #ab47bc 100%)"},
    "アイリスクォーツ": {"primary": "#37474f", "secondary": "#90a4ae", "accent": "#e0f7fa", "gradient": "linear-gradient(135deg, #263238 0%, #546e7a 30%, #e0f7fa 60%, #f3e5f5 100%)"},
}
DEFAULT_COLORS = {"primary": "#37474f", "secondary": "#78909c", "accent": "#cfd8dc", "gradient": "linear-gradient(135deg, #1c313a 0%, #37474f 40%, #78909c 100%)"}


def get_stone_colors(stone_name: str) -> dict:
    """石のカラーテーマを取得"""
    return STONE_COLORS.get(stone_name, DEFAULT_COLORS)


def _file_cache_path(cache_key: str) -> str:
    """キャッシュキーからファイルパスを生成"""
    safe = hashlib.md5(cache_key.encode()).hexdigest()
    return os.path.join(_FILE_CACHE_DIR, f"{safe}.txt")


def _read_file_cache(cache_key: str) -> str | None:
    """ファイルキャッシュからデータURIを読み込む"""
    if not _FILE_CACHE_DIR:
        return None
    try:
        path = _file_cache_path(cache_key)
        if os.path.exists(path):
            with open(path, "r") as f:
                data = f.read()
            if data.startswith("data:"):
                logger.info(f"ファイルキャッシュヒット: {cache_key}")
                return data
    except Exception as e:
        logger.debug(f"ファイルキャッシュ読み込みエラー: {e}")
    return None


def _write_file_cache(cache_key: str, data_uri: str) -> None:
    """ファイルキャッシュにデータURIを保存"""
    if not _FILE_CACHE_DIR:
        return
    try:
        with open(_file_cache_path(cache_key), "w") as f:
            f.write(data_uri)
        logger.info(f"ファイルキャッシュ保存: {cache_key}")
    except Exception as e:
        logger.debug(f"ファイルキャッシュ保存エラー: {e}")


def _generate_image_gemini(prompt: str, cache_key: str = "") -> str | None:
    """Gemini APIで画像を生成し、base64データURIを返す

    Args:
        prompt: 画像生成プロンプト（英語推奨）
        cache_key: キャッシュキー（空ならキャッシュしない）

    Returns:
        "data:image/png;base64,..." 形式のデータURI。失敗時はNone。
    """
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY が設定されていません。画像生成をスキップします。")
        return None

    # 1. インメモリキャッシュチェック（最速）
    if cache_key and cache_key in _image_cache:
        logger.info(f"メモリキャッシュヒット: {cache_key}")
        return _image_cache[cache_key]

    # 2. ファイルキャッシュチェック（コールドスタート後も有効）
    if cache_key:
        cached = _read_file_cache(cache_key)
        if cached:
            # メモリキャッシュにも載せておく
            _image_cache[cache_key] = cached
            return cached

    try:
        resp = requests.post(
            GEMINI_ENDPOINT,
            headers={
                "x-goog-api-key": GEMINI_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseModalities": ["IMAGE"],
                    "imageConfig": {
                        "aspectRatio": "16:9",
                        "imageSize": "1K",
                    },
                },
            },
            timeout=30,
        )

        if resp.status_code != 200:
            logger.warning(f"Gemini画像生成エラー: HTTP {resp.status_code} - {resp.text[:200]}")
            return None

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            logger.warning("Gemini画像生成: 候補なし")
            return None

        for part in candidates[0].get("content", {}).get("parts", []):
            inline_data = part.get("inlineData")
            if inline_data and inline_data.get("data"):
                mime = inline_data.get("mimeType", "image/png")
                b64 = inline_data["data"]
                data_uri = f"data:{mime};base64,{b64}"

                # インメモリキャッシュ保存
                if cache_key:
                    if len(_image_cache) >= CACHE_MAX_SIZE:
                        oldest = next(iter(_image_cache))
                        del _image_cache[oldest]
                    _image_cache[cache_key] = data_uri
                    # ファイルキャッシュにも保存（コールドスタート後に再利用）
                    _write_file_cache(cache_key, data_uri)

                return data_uri

        logger.warning("Gemini画像生成: 画像データなし")
        return None

    except requests.Timeout:
        logger.warning("Gemini画像生成: タイムアウト")
        return None
    except Exception as e:
        logger.warning(f"Gemini画像生成エラー: {e}")
        return None


def _build_cache_key(prefix: str, seed: str) -> str:
    """キャッシュキーを構築"""
    return f"{prefix}-{hashlib.md5(seed.encode()).hexdigest()[:12]}"


def generate_oracle_card_image(card_name: str, card_name_en: str, is_upright: bool, seed_key: str = "") -> str | None:
    """オラクルカード画像を生成する"""
    position = "upright position, radiating light" if is_upright else "reversed position, with shadow"
    prompt = (
        f"A mystical oracle tarot card featuring a {card_name_en} gemstone crystal, "
        f"{position}. Ornate golden art nouveau border frame with intricate patterns. "
        "Dark velvet background with sacred geometry. "
        "Ethereal divine light rays emanating from the crystal. "
        "Fantasy tarot card illustration, highly detailed, magical atmosphere. "
        "No text on the card."
    )
    cache = _build_cache_key("oracle", seed_key) if seed_key else ""
    return _generate_image_gemini(prompt, cache)


def generate_destiny_scene(element_lack_ja: str, stone_name: str, seed_key: str = "") -> str | None:
    """運命の地図シーン画像を生成する"""
    element_scenes = {
        "火": "volcanic landscape with warm aurora and golden flames dancing across a twilight sky, ember particles",
        "地": "ancient crystal cave with glowing minerals, moss-covered stones surrounded by earthen energy and roots",
        "風": "floating sky islands among swirling clouds with ethereal wind currents and shimmering starlight",
        "水": "moonlit underwater temple with bioluminescent coral and jellyfish, calm ocean surface reflecting stars",
    }
    scene = element_scenes.get(element_lack_ja, "cosmic nebula with swirling galaxies and constellation patterns")

    prompt = (
        f"A breathtaking fantasy landscape: {scene}. "
        f"A glowing {stone_name} gemstone crystal floating in the center, emanating mystical energy. "
        "Dreamlike ethereal atmosphere, constellation patterns in the sky. "
        "Digital painting, artstation quality, ultra detailed, no text, no people."
    )
    cache = _build_cache_key("destiny", seed_key) if seed_key else ""
    return _generate_image_gemini(prompt, cache)


def generate_element_balance(fire: int, earth: int, wind: int, water: int, seed_key: str = "") -> str | None:
    """エレメントバランス画像を生成する"""
    dominant = max([("fire", fire), ("earth", earth), ("wind", wind), ("water", water)], key=lambda x: x[1])[0]
    moods = {
        "fire": "fiery red and gold energy orb glowing intensely",
        "earth": "earthy brown and emerald green crystal formation",
        "wind": "silver and white swirling wind current with sparkles",
        "water": "deep blue and teal flowing water stream with moonlight",
    }
    dominant_mood = moods.get(dominant, "balanced cosmic energy")

    prompt = (
        "Four elemental energy orbs floating in a cosmic mandala: "
        f"fire (red), earth (green), wind (white), water (blue). {dominant_mood} is dominant and largest. "
        "Sacred geometry background, abstract spiritual visualization, "
        "glowing particles, symmetrical composition, ethereal digital art, no text."
    )
    cache = _build_cache_key("element", seed_key) if seed_key else ""
    return _generate_image_gemini(prompt, cache)


def generate_bracelet_image(main_stone: str, sub_stones: list[str] | None = None, seed_key: str = "") -> str | None:
    """ブレスレット提案画像を生成する"""
    stones_desc = main_stone
    if sub_stones:
        stones_desc += " with " + " and ".join(sub_stones) + " accent beads"

    prompt = (
        f"A luxury handcrafted gemstone bracelet featuring polished {stones_desc}. "
        "Elegant Japanese spiritual jewelry on white silk fabric. "
        "Soft warm studio lighting, shallow depth of field with bokeh. "
        "High-end jewelry product photography, close-up, ultra detailed, no text."
    )
    cache = _build_cache_key("bracelet", seed_key) if seed_key else ""
    return _generate_image_gemini(prompt, cache)
