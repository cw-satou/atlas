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


def get_product(product_id: int | str) -> ProductEntry | None:
    """WooCommerce product_idで商品構成を取得する"""
    return PRODUCT_MASTER.get(str(product_id))


def get_enabled_products(config: dict | None = None) -> list[ProductEntry]:
    """有効な商品構成の一覧を返す（configオーバーライド対応）"""
    result = []
    for pid, p in PRODUCT_MASTER.items():
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
