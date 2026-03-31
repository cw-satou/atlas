"""石マスタ

各天然石の特性（エレメント・オーラ・占星術・数秘・色・テーマ・悩み）を定義する。
商品構成マスタと組み合わせて商品の特性を自動計算するために使用する。
"""

# ===== オーラ分類定義 =====

AURA_CATEGORIES = [
    "intuition",   # 直感
    "clarity",     # 明晰
    "stability",   # 安定
    "vitality",    # 活力
    "protection",  # 保護
    "love",        # 愛情
    "expression",  # 表現
    "courage",     # 勇気
]

# ===== 石マスタ =====

STONE_MASTER: dict = {

    "lapis_lazuli": {
        "stone_name": "ラピスラズリ",
        "description": "真実と直感の石。精神を高め、深い洞察を与える。",
        "element_profile": {"fire": 0.1, "earth": 0.2, "air": 0.7, "water": 0.8},
        "aura_profile": {
            "intuition": 0.9, "clarity": 0.8, "stability": 0.4,
            "vitality": 0.2, "protection": 0.6, "love": 0.3,
            "expression": 0.5, "courage": 0.4,
        },
        "zodiac": ["sagittarius", "pisces"],
        "planet": ["jupiter"],
        "birth_month": [9, 12],
        "numerology_affinity": [7, 9],
        "color_tags": ["blue", "gold"],
        "theme_tags": ["直感", "真実", "自己理解", "知性"],
        "worry_tags": ["迷い", "不安", "方向性", "自信不足"],
        "weight": 1.0,
    },

    "carnelian": {
        "stone_name": "カーネリアン",
        "description": "情熱と行動力の石。創造性と勇気を引き出す。",
        "element_profile": {"fire": 0.9, "earth": 0.5, "air": 0.3, "water": 0.1},
        "aura_profile": {
            "intuition": 0.3, "clarity": 0.4, "stability": 0.5,
            "vitality": 0.9, "protection": 0.5, "love": 0.6,
            "expression": 0.8, "courage": 0.9,
        },
        "zodiac": ["aries", "leo", "virgo"],
        "planet": ["sun", "mars"],
        "birth_month": [7, 8],
        "numerology_affinity": [1, 3, 5],
        "color_tags": ["orange", "red"],
        "theme_tags": ["行動力", "情熱", "創造性", "自己表現"],
        "worry_tags": ["やる気がでない", "踏み出せない", "停滞感"],
        "weight": 1.0,
    },

    "malachite": {
        "stone_name": "マラカイト",
        "description": "変容と癒しの石。感情を浄化し、前進する力を与える。",
        "element_profile": {"fire": 0.3, "earth": 0.8, "air": 0.4, "water": 0.6},
        "aura_profile": {
            "intuition": 0.5, "clarity": 0.6, "stability": 0.7,
            "vitality": 0.5, "protection": 0.8, "love": 0.6,
            "expression": 0.4, "courage": 0.6,
        },
        "zodiac": ["taurus", "scorpio", "capricorn"],
        "planet": ["venus"],
        "birth_month": [5],
        "numerology_affinity": [4, 6, 8],
        "color_tags": ["green"],
        "theme_tags": ["変容", "癒し", "前進", "保護"],
        "worry_tags": ["変化への恐れ", "感情の揺れ", "人間関係"],
        "weight": 1.0,
    },

    "amethyst": {
        "stone_name": "アメジスト",
        "description": "精神と直感の石。心を落ち着かせ、深い洞察を与える。",
        "element_profile": {"fire": 0.1, "earth": 0.2, "air": 0.6, "water": 0.9},
        "aura_profile": {
            "intuition": 0.9, "clarity": 0.8, "stability": 0.7,
            "vitality": 0.2, "protection": 0.7, "love": 0.5,
            "expression": 0.4, "courage": 0.3,
        },
        "zodiac": ["aquarius", "pisces", "virgo"],
        "planet": ["neptune", "jupiter"],
        "birth_month": [2],
        "numerology_affinity": [3, 7, 9],
        "color_tags": ["purple"],
        "theme_tags": ["精神統一", "直感", "癒し", "浄化"],
        "worry_tags": ["不安", "ストレス", "眠れない", "焦り"],
        "weight": 1.0,
    },

    "rose_quartz": {
        "stone_name": "ローズクォーツ",
        "description": "愛と優しさの石。自己愛を育み、人間関係を和らげる。",
        "element_profile": {"fire": 0.2, "earth": 0.4, "air": 0.5, "water": 0.8},
        "aura_profile": {
            "intuition": 0.4, "clarity": 0.3, "stability": 0.6,
            "vitality": 0.4, "protection": 0.5, "love": 1.0,
            "expression": 0.5, "courage": 0.3,
        },
        "zodiac": ["taurus", "libra", "cancer"],
        "planet": ["venus"],
        "birth_month": [1, 10],
        "numerology_affinity": [2, 6],
        "color_tags": ["pink"],
        "theme_tags": ["愛情", "自己愛", "調和", "優しさ"],
        "worry_tags": ["恋愛", "人間関係", "孤独感", "自己否定"],
        "weight": 1.0,
    },

    "crystal": {
        "stone_name": "水晶",
        "description": "浄化と増幅の石。あらゆるエネルギーを高める万能石。",
        "element_profile": {"fire": 0.5, "earth": 0.5, "air": 0.5, "water": 0.5},
        "aura_profile": {
            "intuition": 0.6, "clarity": 0.9, "stability": 0.6,
            "vitality": 0.6, "protection": 0.6, "love": 0.5,
            "expression": 0.6, "courage": 0.5,
        },
        "zodiac": [
            "aries", "taurus", "gemini", "cancer", "leo", "virgo",
            "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
        ],
        "planet": ["sun"],
        "birth_month": [4],
        "numerology_affinity": [1, 2, 3, 4, 5, 6, 7, 8, 9],
        "color_tags": ["clear", "white"],
        "theme_tags": ["浄化", "増幅", "調和", "万能"],
        "worry_tags": ["何となく不調", "気の滞り", "全般的な浄化"],
        "weight": 1.0,
    },

    "aquamarine": {
        "stone_name": "アクアマリン",
        "description": "勇気と冷静さの石。感情を穏やかにし、コミュニケーションを助ける。",
        "element_profile": {"fire": 0.1, "earth": 0.2, "air": 0.7, "water": 0.9},
        "aura_profile": {
            "intuition": 0.6, "clarity": 0.8, "stability": 0.7,
            "vitality": 0.3, "protection": 0.5, "love": 0.5,
            "expression": 0.7, "courage": 0.7,
        },
        "zodiac": ["pisces", "aquarius", "gemini"],
        "planet": ["neptune", "mercury"],
        "birth_month": [3],
        "numerology_affinity": [1, 3],
        "color_tags": ["lightblue"],
        "theme_tags": ["冷静さ", "コミュニケーション", "勇気", "癒し"],
        "worry_tags": ["感情の揺れ", "人間関係", "言葉が出ない", "緊張"],
        "weight": 1.0,
    },

    "tiger_eye": {
        "stone_name": "タイガーアイ",
        "description": "実現力と洞察の石。目標達成と財運を強化する。",
        "element_profile": {"fire": 0.7, "earth": 0.8, "air": 0.3, "water": 0.2},
        "aura_profile": {
            "intuition": 0.6, "clarity": 0.7, "stability": 0.8,
            "vitality": 0.8, "protection": 0.7, "love": 0.2,
            "expression": 0.5, "courage": 0.8,
        },
        "zodiac": ["leo", "capricorn", "gemini"],
        "planet": ["sun", "saturn"],
        "birth_month": [11],
        "numerology_affinity": [4, 8],
        "color_tags": ["brown", "gold"],
        "theme_tags": ["金運", "実現力", "洞察", "目標達成"],
        "worry_tags": ["金運", "仕事", "目標が見えない", "決断できない"],
        "weight": 1.0,
    },

    "moonstone": {
        "stone_name": "ムーンストーン",
        "description": "直感と女性性の石。感情のリズムを整え、変化を穏やかに乗り越える。",
        "element_profile": {"fire": 0.1, "earth": 0.3, "air": 0.5, "water": 0.9},
        "aura_profile": {
            "intuition": 0.9, "clarity": 0.5, "stability": 0.5,
            "vitality": 0.3, "protection": 0.6, "love": 0.8,
            "expression": 0.5, "courage": 0.3,
        },
        "zodiac": ["cancer", "libra", "pisces"],
        "planet": ["moon"],
        "birth_month": [6],
        "numerology_affinity": [2, 7],
        "color_tags": ["white", "clear"],
        "theme_tags": ["直感", "女性性", "感情", "変化"],
        "worry_tags": ["感情の揺れ", "生理周期", "変化への不安", "恋愛"],
        "weight": 1.0,
    },

    "garnet": {
        "stone_name": "ガーネット",
        "description": "情熱と生命力の石。活力を高め、意志を強化する。",
        "element_profile": {"fire": 0.9, "earth": 0.5, "air": 0.2, "water": 0.2},
        "aura_profile": {
            "intuition": 0.3, "clarity": 0.4, "stability": 0.6,
            "vitality": 0.9, "protection": 0.7, "love": 0.7,
            "expression": 0.6, "courage": 0.8,
        },
        "zodiac": ["aries", "leo", "scorpio"],
        "planet": ["mars"],
        "birth_month": [1],
        "numerology_affinity": [1, 9],
        "color_tags": ["red", "dark_red"],
        "theme_tags": ["情熱", "活力", "愛情", "意志"],
        "worry_tags": ["やる気がでない", "疲労感", "恋愛", "勇気が出ない"],
        "weight": 1.0,
    },

    "onyx": {
        "stone_name": "オニキス",
        "description": "防護と意志の石。ネガティブなエネルギーを遮断し、精神を強化する。",
        "element_profile": {"fire": 0.4, "earth": 0.9, "air": 0.2, "water": 0.3},
        "aura_profile": {
            "intuition": 0.4, "clarity": 0.6, "stability": 0.9,
            "vitality": 0.6, "protection": 1.0, "love": 0.2,
            "expression": 0.3, "courage": 0.8,
        },
        "zodiac": ["capricorn", "leo", "aries"],
        "planet": ["saturn", "mars"],
        "birth_month": [7],
        "numerology_affinity": [4, 8],
        "color_tags": ["black"],
        "theme_tags": ["保護", "防護", "意志", "強化"],
        "worry_tags": ["ネガティブ思考", "他人の影響を受けやすい", "境界線"],
        "weight": 1.0,
    },

    "citrine": {
        "stone_name": "シトリン",
        "description": "豊かさと明るさの石。ポジティブなエネルギーと金運を引き寄せる。",
        "element_profile": {"fire": 0.7, "earth": 0.7, "air": 0.5, "water": 0.1},
        "aura_profile": {
            "intuition": 0.4, "clarity": 0.7, "stability": 0.6,
            "vitality": 0.8, "protection": 0.3, "love": 0.5,
            "expression": 0.7, "courage": 0.6,
        },
        "zodiac": ["gemini", "leo", "aries", "libra"],
        "planet": ["sun", "mercury"],
        "birth_month": [11],
        "numerology_affinity": [3, 6],
        "color_tags": ["yellow"],
        "theme_tags": ["金運", "豊かさ", "明るさ", "ポジティブ"],
        "worry_tags": ["金運", "自信不足", "ネガティブ思考", "停滞感"],
        "weight": 1.0,
    },

    "sea_blue_chalcedony": {
        "stone_name": "シーブルーカルセドニー",
        "description": "静けさと癒しの石。心を穏やかにし、コミュニケーションを助ける。",
        "element_profile": {"fire": 0.1, "earth": 0.3, "air": 0.7, "water": 0.9},
        "aura_profile": {
            "intuition": 0.6, "clarity": 0.7, "stability": 0.8,
            "vitality": 0.3, "protection": 0.5, "love": 0.6,
            "expression": 0.7, "courage": 0.5,
        },
        "zodiac": ["gemini", "aquarius", "pisces"],
        "planet": ["moon", "mercury"],
        "birth_month": [3, 6],
        "numerology_affinity": [2, 7],
        "color_tags": ["lightblue", "blue"],
        "theme_tags": ["癒し", "静けさ", "コミュニケーション", "穏やか"],
        "worry_tags": ["ストレス", "人間関係", "感情の揺れ", "緊張"],
        "weight": 1.0,
    },

    "madagascar_rose_quartz": {
        "stone_name": "マダガスカル産ローズクォーツ",
        "description": "最上質の愛の石。強い愛のエネルギーで心を包み込む。",
        "element_profile": {"fire": 0.2, "earth": 0.3, "air": 0.5, "water": 0.9},
        "aura_profile": {
            "intuition": 0.5, "clarity": 0.4, "stability": 0.6,
            "vitality": 0.4, "protection": 0.5, "love": 1.0,
            "expression": 0.6, "courage": 0.3,
        },
        "zodiac": ["taurus", "libra", "cancer"],
        "planet": ["venus"],
        "birth_month": [1, 10],
        "numerology_affinity": [2, 6],
        "color_tags": ["pink"],
        "theme_tags": ["愛情", "自己愛", "調和", "癒し"],
        "worry_tags": ["恋愛", "人間関係", "自己否定", "孤独感"],
        "weight": 1.1,
    },

}


import time as _time

# シートキャッシュ（TTL: 300秒）
_sheet_cache: dict = {"data": None, "expires": 0.0}


def _load_from_sheet() -> dict | None:
    """stone_masterシートからデータを読み込む（失敗時はNone）"""
    try:
        from api.utils_sheet import get_stone_master_from_sheet
        return get_stone_master_from_sheet()
    except Exception:
        return None


def get_stone_master_data() -> dict:
    """シート優先でマスターデータを返す（失敗時はハードコードにフォールバック）"""
    now = _time.time()
    if _sheet_cache["data"] and now < _sheet_cache["expires"]:
        return _sheet_cache["data"]
    data = _load_from_sheet()
    if data:
        _sheet_cache["data"] = data
        _sheet_cache["expires"] = now + 300
        return data
    return STONE_MASTER


def invalidate_stone_master_cache() -> None:
    """石マスターのメモリキャッシュを破棄してシートから再読み込みさせる"""
    _sheet_cache["data"] = None
    _sheet_cache["expires"] = 0.0


def get_stone(stone_id: str) -> dict | None:
    """石IDで石データを取得する"""
    return get_stone_master_data().get(stone_id)


def get_all_stone_ids() -> list[str]:
    """全石IDのリストを返す"""
    return list(get_stone_master_data().keys())
