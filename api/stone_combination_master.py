"""石の組み合わせマスタ

石同士の相乗効果を定義する。
単石の意味を超えた、組み合わせ固有の意味・補正値を持つ。
キーはstone_idのfrozenset（順序不問）。
"""

from typing import TypedDict


class CombinationEffect(TypedDict):
    theme_tags: list[str]
    worry_tags: list[str]
    element_bonus: dict[str, float]
    aura_bonus: dict[str, float]
    meaning: str
    weight: float


# ===== 組み合わせマスタ =====
# キー：frozenset({stone_id_a, stone_id_b})

STONE_COMBINATION_MASTER: dict[frozenset, CombinationEffect] = {

    frozenset({"lapis_lazuli", "crystal"}): {
        "theme_tags": ["直感強化", "本質理解", "気づき"],
        "worry_tags": ["迷い", "判断不安"],
        "element_bonus": {"air": 0.1, "water": 0.1},
        "aura_bonus": {"intuition": 0.2, "clarity": 0.2},
        "meaning": "直感と明晰さを高め、本質への気づきを深める",
        "weight": 1.0,
    },

    frozenset({"lapis_lazuli", "aquamarine"}): {
        "theme_tags": ["自己表現", "真実の言葉", "対話"],
        "worry_tags": ["言葉が出ない", "誤解される", "人間関係"],
        "element_bonus": {"air": 0.15, "water": 0.15},
        "aura_bonus": {"expression": 0.2, "clarity": 0.15},
        "meaning": "真実を穏やかに伝える力を引き出す",
        "weight": 1.0,
    },

    frozenset({"amethyst", "crystal"}): {
        "theme_tags": ["精神浄化", "瞑想", "高次元接続"],
        "worry_tags": ["不安", "ストレス", "気の滞り"],
        "element_bonus": {"air": 0.1, "water": 0.1},
        "aura_bonus": {"intuition": 0.2, "clarity": 0.15, "stability": 0.1},
        "meaning": "精神を深く浄化し、静寂の中に気づきをもたらす",
        "weight": 1.0,
    },

    frozenset({"amethyst", "moonstone"}): {
        "theme_tags": ["女性性", "直感", "感情の流れ"],
        "worry_tags": ["感情の揺れ", "生理周期", "恋愛"],
        "element_bonus": {"water": 0.2},
        "aura_bonus": {"intuition": 0.25, "love": 0.15},
        "meaning": "感情の流れに乗り、深い直感を開花させる",
        "weight": 1.0,
    },

    frozenset({"rose_quartz", "crystal"}): {
        "theme_tags": ["愛の増幅", "自己愛強化", "調和"],
        "worry_tags": ["恋愛", "自己否定", "孤独感"],
        "element_bonus": {"water": 0.1},
        "aura_bonus": {"love": 0.25, "stability": 0.1},
        "meaning": "愛のエネルギーを増幅し、自己愛を強く育む",
        "weight": 1.0,
    },

    frozenset({"rose_quartz", "moonstone"}): {
        "theme_tags": ["女性性", "愛情", "柔らかさ"],
        "worry_tags": ["恋愛", "感情の揺れ", "自己否定"],
        "element_bonus": {"water": 0.2},
        "aura_bonus": {"love": 0.2, "intuition": 0.15},
        "meaning": "女性性を高め、愛情と直感を同時に開く",
        "weight": 1.0,
    },

    frozenset({"carnelian", "tiger_eye"}): {
        "theme_tags": ["行動力", "目標達成", "実現力"],
        "worry_tags": ["踏み出せない", "仕事", "目標が見えない"],
        "element_bonus": {"fire": 0.2, "earth": 0.15},
        "aura_bonus": {"vitality": 0.2, "courage": 0.2},
        "meaning": "情熱と実現力を合わせ、目標を力強く引き寄せる",
        "weight": 1.0,
    },

    frozenset({"garnet", "tiger_eye"}): {
        "theme_tags": ["意志力", "金運", "情熱的な実現"],
        "worry_tags": ["金運", "仕事", "やる気がでない"],
        "element_bonus": {"fire": 0.2, "earth": 0.15},
        "aura_bonus": {"vitality": 0.2, "courage": 0.15},
        "meaning": "情熱を現実に変える強いエネルギーを作る",
        "weight": 1.0,
    },

    frozenset({"onyx", "tiger_eye"}): {
        "theme_tags": ["防護", "洞察", "強い意志"],
        "worry_tags": ["他人の影響を受けやすい", "境界線", "ネガティブ思考"],
        "element_bonus": {"earth": 0.2},
        "aura_bonus": {"protection": 0.2, "stability": 0.15},
        "meaning": "外部の影響を遮断し、自分軸で前進する力を与える",
        "weight": 1.0,
    },

    frozenset({"citrine", "crystal"}): {
        "theme_tags": ["豊かさの増幅", "ポジティブ強化", "金運"],
        "worry_tags": ["金運", "ネガティブ思考", "停滞感"],
        "element_bonus": {"fire": 0.1, "earth": 0.1},
        "aura_bonus": {"vitality": 0.15, "clarity": 0.15},
        "meaning": "ポジティブなエネルギーを増幅し、豊かさを引き寄せる",
        "weight": 1.0,
    },

    frozenset({"malachite", "crystal"}): {
        "theme_tags": ["変容の促進", "浄化と再生", "前進"],
        "worry_tags": ["変化への恐れ", "感情の揺れ", "古い習慣"],
        "element_bonus": {"earth": 0.1, "water": 0.1},
        "aura_bonus": {"protection": 0.15, "clarity": 0.15},
        "meaning": "深い浄化と変容を促し、新しい自分へ向かう力を与える",
        "weight": 1.0,
    },

    frozenset({"aquamarine", "moonstone"}): {
        "theme_tags": ["感情と表現", "穏やかな勇気", "流れに乗る"],
        "worry_tags": ["緊張", "感情の揺れ", "変化への不安"],
        "element_bonus": {"water": 0.2, "air": 0.1},
        "aura_bonus": {"expression": 0.15, "stability": 0.15},
        "meaning": "感情を穏やかに整え、自分らしい言葉で前に進む力を与える",
        "weight": 1.0,
    },

}


import time as _time

# シートキャッシュ（TTL: 300秒）
_sheet_cache: dict = {"data": None, "expires": 0.0}


def _load_from_sheet() -> dict | None:
    """stone_combinationsシートからデータを読み込む（失敗時はNone）"""
    try:
        from api.utils_sheet import get_combination_master_from_sheet
        return get_combination_master_from_sheet()
    except Exception:
        return None


def get_combination_master_data() -> dict:
    """シート優先で組み合わせマスターデータを返す（失敗時はハードコードにフォールバック）"""
    now = _time.time()
    if _sheet_cache["data"] and now < _sheet_cache["expires"]:
        return _sheet_cache["data"]
    data = _load_from_sheet()
    if data:
        _sheet_cache["data"] = data
        _sheet_cache["expires"] = now + 300
        return data
    return STONE_COMBINATION_MASTER


def invalidate_combination_master_cache() -> None:
    """組み合わせマスターのメモリキャッシュを破棄してシートから再読み込みさせる"""
    _sheet_cache["data"] = None
    _sheet_cache["expires"] = 0.0


def get_combination_effect(stone_id_a: str, stone_id_b: str) -> CombinationEffect | None:
    """2つの石IDの組み合わせ効果を取得する。なければNoneを返す。"""
    key = frozenset({stone_id_a, stone_id_b})
    return get_combination_master_data().get(key)
