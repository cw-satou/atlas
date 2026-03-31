"""商品構成マスタ

WooCommerceの商品IDと石構成だけを持つ最小入力方式。
エレメント・オーラ・数秘・テーマ・悩みはマッチングエンジンが石マスタから自動計算する。
"""

from typing import TypedDict


class StonePart(TypedDict):
    stone_id: str          # stone_master.py のキー
    role: str              # "main" / "sub" / "round"
    size: int              # mm（例：8, 10, 12）


class ProductEntry(TypedDict):
    woo_product_id: int
    sku: str
    parts: list[StonePart]
    gender_mode: str       # "male" / "female" / "unisex"
    enabled: bool
    priority_weight: float


# ===== 商品構成マスタ =====
# キーはWooCommerce product_idの文字列表現

PRODUCT_MASTER: dict[str, ProductEntry] = {

    "1203": {
        "woo_product_id": 1203,
        "sku": "bracelet-lapis-gray",
        "parts": [
            {"stone_id": "lapis_lazuli", "role": "main", "size": 12},
            {"stone_id": "crystal",      "role": "round", "size": 8},
        ],
        "gender_mode": "unisex",
        "enabled": True,
        "priority_weight": 1.0,
    },

    "1204": {
        "woo_product_id": 1204,
        "sku": "bracelet-carnelian-gray",
        "parts": [
            {"stone_id": "carnelian", "role": "main", "size": 12},
            {"stone_id": "crystal",   "role": "round", "size": 8},
        ],
        "gender_mode": "unisex",
        "enabled": True,
        "priority_weight": 1.0,
    },

    "1205": {
        "woo_product_id": 1205,
        "sku": "bracelet-malachite-gray",
        "parts": [
            {"stone_id": "malachite", "role": "main", "size": 12},
            {"stone_id": "crystal",   "role": "round", "size": 8},
        ],
        "gender_mode": "unisex",
        "enabled": True,
        "priority_weight": 1.0,
    },

    "1206": {
        "woo_product_id": 1206,
        "sku": "bracelet-amethyst-gray",
        "parts": [
            {"stone_id": "amethyst", "role": "main", "size": 12},
            {"stone_id": "crystal",  "role": "round", "size": 8},
        ],
        "gender_mode": "unisex",
        "enabled": True,
        "priority_weight": 1.0,
    },

    "1207": {
        "woo_product_id": 1207,
        "sku": "bracelet-iris-lapis-gray",
        "parts": [
            {"stone_id": "lapis_lazuli", "role": "main",  "size": 12},
            {"stone_id": "amethyst",     "role": "sub",   "size": 10},
            {"stone_id": "crystal",      "role": "round", "size": 8},
        ],
        "gender_mode": "unisex",
        "enabled": True,
        "priority_weight": 1.1,
    },

    "1208": {
        "woo_product_id": 1208,
        "sku": "bracelet-iris-carnelian-gray",
        "parts": [
            {"stone_id": "carnelian", "role": "main",  "size": 12},
            {"stone_id": "tiger_eye", "role": "sub",   "size": 10},
            {"stone_id": "crystal",   "role": "round", "size": 8},
        ],
        "gender_mode": "unisex",
        "enabled": True,
        "priority_weight": 1.1,
    },

    "1209": {
        "woo_product_id": 1209,
        "sku": "bracelet-iris-malachite-gray",
        "parts": [
            {"stone_id": "malachite", "role": "main",  "size": 12},
            {"stone_id": "onyx",      "role": "sub",   "size": 10},
            {"stone_id": "crystal",   "role": "round", "size": 8},
        ],
        "gender_mode": "unisex",
        "enabled": True,
        "priority_weight": 1.1,
    },

    "1210": {
        "woo_product_id": 1210,
        "sku": "bracelet-iris-amethyst-gray",
        "parts": [
            {"stone_id": "amethyst",  "role": "main",  "size": 12},
            {"stone_id": "moonstone", "role": "sub",   "size": 10},
            {"stone_id": "crystal",   "role": "round", "size": 8},
        ],
        "gender_mode": "unisex",
        "enabled": True,
        "priority_weight": 1.1,
    },

    "1201": {
        "woo_product_id": 1201,
        "sku": "bracelet-shizukanaumi",
        "parts": [
            {"stone_id": "sea_blue_chalcedony", "role": "main",  "size": 12},
            {"stone_id": "aquamarine",          "role": "sub",   "size": 10},
            {"stone_id": "crystal",             "role": "round", "size": 8},
        ],
        "gender_mode": "female",
        "enabled": True,
        "priority_weight": 1.0,
    },

    "1202": {
        "woo_product_id": 1202,
        "sku": "bracelet-yasashiitsuki",
        "parts": [
            {"stone_id": "madagascar_rose_quartz", "role": "main",  "size": 12},
            {"stone_id": "moonstone",              "role": "sub",   "size": 10},
            {"stone_id": "rose_quartz",            "role": "round", "size": 8},
        ],
        "gender_mode": "female",
        "enabled": True,
        "priority_weight": 1.0,
    },

}


import time as _time

# シートキャッシュ（TTL: 300秒）
_sheet_cache: dict = {"data": None, "expires": 0.0}


def _load_from_sheet() -> dict | None:
    """product_masterシートからデータを読み込む（失敗時はNone）"""
    try:
        from api.utils_sheet import get_product_master_from_sheet
        return get_product_master_from_sheet()
    except Exception:
        return None


def get_product_master_data() -> dict:
    """シート優先で商品マスターデータを返す（失敗時はハードコードにフォールバック）"""
    now = _time.time()
    if _sheet_cache["data"] and now < _sheet_cache["expires"]:
        return _sheet_cache["data"]
    data = _load_from_sheet()
    if data:
        _sheet_cache["data"] = data
        _sheet_cache["expires"] = now + 300
        return data
    return PRODUCT_MASTER


def invalidate_product_master_cache() -> None:
    """商品マスターのメモリキャッシュを破棄してシートから再読み込みさせる"""
    _sheet_cache["data"] = None
    _sheet_cache["expires"] = 0.0


def get_product(product_id: int | str) -> ProductEntry | None:
    """WooCommerce product_idで商品構成を取得する"""
    return get_product_master_data().get(str(product_id))


def get_enabled_products(config: dict | None = None) -> list[ProductEntry]:
    """有効な商品構成の一覧を返す（configオーバーライド対応）"""
    result = []
    for pid, p in get_product_master_data().items():
        entry = dict(p)
        if config:
            enabled_key = f"product_{pid}_enabled"
            priority_key = f"product_{pid}_priority"
            if enabled_key in config:
                entry["enabled"] = str(config[enabled_key]).lower() == "true"
            if priority_key in config:
                try:
                    entry["priority_weight"] = float(config[priority_key])
                except (ValueError, TypeError):
                    pass
        if entry["enabled"]:
            result.append(entry)
    return result
