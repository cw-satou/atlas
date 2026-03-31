"""画像生成モジュール

Gemini API（gemini-3.1-flash-image-preview）を使って診断結果に合わせた
イメージ画像を生成する。

キャッシュ戦略（3層）:
  1. インメモリ  - 同一プロセス内で最速再利用
  2. /tmp ファイル - Vercel同一コンテナ内で永続（コールドスタート後も数時間有効）
  3. Google Drive  - 恒久保存。DRIVE_IMAGE_FOLDER_IDが設定されていれば使用

Drive保存時は base64 ではなく Drive の公開URLを返すため、
フロントの <img src="..."> に直接使える。

環境変数:
    GEMINI_API_KEY            : Google AI Studio / Gemini APIのAPIキー
    DRIVE_IMAGE_FOLDER_ID     : 画像を保存するGoogle DriveフォルダのID
    GOOGLE_SERVICE_ACCOUNT_JSON: Drive認証用サービスアカウントJSON（Sheets共通）
"""

import os
import io
import json
import base64
import hashlib
import logging
import requests

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-3.1-flash-image-preview"
GEMINI_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

DRIVE_IMAGE_FOLDER_ID = os.environ.get("DRIVE_IMAGE_FOLDER_ID", "")

# ===== キャッシュ設定 =====

# 1. インメモリキャッシュ
_image_cache: dict[str, str] = {}
CACHE_MAX_SIZE = 20

# 2. /tmp ファイルキャッシュ
_FILE_CACHE_DIR = os.path.join(os.environ.get("TMPDIR", "/tmp"), "atlas_img_cache")
try:
    os.makedirs(_FILE_CACHE_DIR, exist_ok=True)
except Exception:
    _FILE_CACHE_DIR = ""

# 3. Drive APIサービス（遅延初期化）
_drive_service_cache: dict = {"service": None}


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


# ===== キャッシュ操作 =====

def _cache_filename(cache_key: str) -> str:
    """キャッシュキーのMD5ハッシュからファイル名を生成"""
    return hashlib.md5(cache_key.encode()).hexdigest()


def _read_file_cache(cache_key: str) -> str | None:
    """/tmp ファイルキャッシュを読む（Drive URLまたはbase64を返す）"""
    if not _FILE_CACHE_DIR:
        return None
    try:
        path = os.path.join(_FILE_CACHE_DIR, f"{_cache_filename(cache_key)}.txt")
        if os.path.exists(path):
            with open(path, "r") as f:
                data = f.read().strip()
            if data:
                logger.info("ファイルキャッシュヒット: %s", cache_key)
                return data
    except Exception as e:
        logger.debug("ファイルキャッシュ読み込みエラー: %s", e)
    return None


def _write_file_cache(cache_key: str, value: str) -> None:
    """/tmp ファイルキャッシュに書き込む"""
    if not _FILE_CACHE_DIR:
        return
    try:
        path = os.path.join(_FILE_CACHE_DIR, f"{_cache_filename(cache_key)}.txt")
        with open(path, "w") as f:
            f.write(value)
        logger.info("ファイルキャッシュ保存: %s", cache_key)
    except Exception as e:
        logger.debug("ファイルキャッシュ保存エラー: %s", e)


def _get_drive_service():
    """Drive APIサービスを返す（遅延初期化・キャッシュ付き）"""
    if _drive_service_cache["service"]:
        return _drive_service_cache["service"]
    if not DRIVE_IMAGE_FOLDER_ID:
        return None
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not creds_json:
        return None
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        info = json.loads(creds_json)
        creds = Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/drive"],
        )
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        _drive_service_cache["service"] = service
        logger.info("Drive APIサービス初期化完了")
        return service
    except Exception as e:
        logger.warning("Drive APIサービス初期化エラー: %s", e)
        return None


def _drive_file_name(cache_key: str) -> str:
    """キャッシュキーからDriveファイル名を生成"""
    return f"atlas_img_{_cache_filename(cache_key)}.png"


def _find_in_drive(cache_key: str) -> str | None:
    """DriveフォルダにキャッシュキーのファイルがあればURLを返す"""
    service = _get_drive_service()
    if not service:
        return None
    try:
        fname = _drive_file_name(cache_key)
        results = service.files().list(
            q=f"name='{fname}' and '{DRIVE_IMAGE_FOLDER_ID}' in parents and trashed=false",
            fields="files(id)",
            pageSize=1,
        ).execute()
        files = results.get("files", [])
        if files:
            file_id = files[0]["id"]
            url = f"https://drive.google.com/uc?id={file_id}&export=view"
            logger.info("Driveキャッシュヒット: %s → %s", cache_key, file_id)
            return url
    except Exception as e:
        logger.debug("Drive検索エラー: %s", e)
    return None


def _upload_to_drive(data_uri: str, cache_key: str) -> str | None:
    """base64データURIをDriveフォルダにアップロードし公開URLを返す"""
    service = _get_drive_service()
    if not service:
        return None
    try:
        from googleapiclient.http import MediaIoBaseUpload
        # "data:image/png;base64,XXX" からバイト列へ
        _, b64part = data_uri.split(",", 1)
        img_bytes = base64.b64decode(b64part)

        fname = _drive_file_name(cache_key)
        file_metadata = {
            "name": fname,
            "parents": [DRIVE_IMAGE_FOLDER_ID],
        }
        media = MediaIoBaseUpload(
            io.BytesIO(img_bytes),
            mimetype="image/png",
            resumable=False,
        )
        created = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id",
        ).execute()
        file_id = created["id"]

        # 誰でも閲覧できるよう公開設定
        service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()

        url = f"https://drive.google.com/uc?id={file_id}&export=view"
        logger.info("Drive保存完了: %s → %s", cache_key, file_id)
        return url
    except Exception as e:
        logger.warning("Driveアップロードエラー: %s", e)
        return None


def _set_cache(cache_key: str, value: str) -> None:
    """メモリ＋ファイルキャッシュに書き込む"""
    if len(_image_cache) >= CACHE_MAX_SIZE:
        oldest = next(iter(_image_cache))
        del _image_cache[oldest]
    _image_cache[cache_key] = value
    _write_file_cache(cache_key, value)


# ===== メイン画像生成 =====

def _generate_image_gemini(prompt: str, cache_key: str = "") -> str | None:
    """Gemini APIで画像を生成する。

    キャッシュ優先順位:
      1. インメモリ  → Drive URLまたはbase64を即返却
      2. /tmp ファイル → 同上
      3. Google Drive  → URLを取得しキャッシュに載せて返却
      4. Gemini API生成 → Drive保存 or base64のままキャッシュして返却

    Returns:
        DRIVE_IMAGE_FOLDER_IDが設定されている場合: Drive公開URL
        未設定の場合: "data:image/png;base64,..." 形式のデータURI
        失敗時: None
    """
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY が設定されていません。画像生成をスキップします。")
        return None

    # 1. メモリキャッシュ
    if cache_key and cache_key in _image_cache:
        logger.info("メモリキャッシュヒット: %s", cache_key)
        return _image_cache[cache_key]

    # 2. /tmp ファイルキャッシュ
    if cache_key:
        cached = _read_file_cache(cache_key)
        if cached:
            _image_cache[cache_key] = cached
            return cached

    # 3. Google Driveキャッシュ（フォルダID設定時のみ）
    if cache_key and DRIVE_IMAGE_FOLDER_ID:
        drive_url = _find_in_drive(cache_key)
        if drive_url:
            _set_cache(cache_key, drive_url)
            return drive_url

    # 4. Gemini APIで生成
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
                },
            },
            timeout=120,
        )

        if resp.status_code != 200:
            logger.warning("Gemini画像生成エラー: HTTP %s - %s", resp.status_code, resp.text[:200])
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

                if not cache_key:
                    return data_uri

                # Driveフォルダが設定されていればアップロードしてURLを返す
                if DRIVE_IMAGE_FOLDER_ID:
                    drive_url = _upload_to_drive(data_uri, cache_key)
                    if drive_url:
                        _set_cache(cache_key, drive_url)
                        return drive_url
                    # Drive保存失敗時はbase64にフォールバック

                # Driveなし or 保存失敗 → base64をキャッシュ
                _set_cache(cache_key, data_uri)
                return data_uri

        logger.warning("Gemini画像生成: 画像データなし")
        return None

    except requests.Timeout:
        logger.warning("Gemini画像生成: タイムアウト")
        return None
    except Exception as e:
        logger.warning("Gemini画像生成エラー: %s", e)
        return None


def _build_cache_key(prefix: str, seed: str) -> str:
    """キャッシュキーを構築"""
    return f"{prefix}-{hashlib.md5(seed.encode()).hexdigest()[:12]}"


# ===== 各シーン生成関数 =====

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
