"""マッチングエンジン

ユーザーの診断結果と商品構成を照合し、一致率上位3商品を返す。

スコアリング重み（フェーズ1）:
  エレメント一致率 40%
  オーラ一致率    30%
  テーマ一致率    20%
  悩み一致率      10%
"""

import logging
from itertools import combinations

from api.stone_master import get_stone
from api.stone_combination_master import get_combination_effect
from api.role_weight import get_role_weight, get_combination_role_weight
from api.product_master import get_enabled_products, ProductEntry

logger = logging.getLogger(__name__)

# ===== スコアリング重み =====

SCORE_WEIGHTS = {
    "element": 0.35,
    "aura":    0.25,
    "theme":   0.15,
    "worry":   0.25,
}


def get_score_weights() -> dict:
    """configシートのオーバーライドを反映したスコアリング重みを返す（合計1に正規化）"""
    try:
        from api.utils_sheet import get_config
        cfg = get_config()
        weights = dict(SCORE_WEIGHTS)
        for k in ["element", "aura", "theme", "worry"]:
            key = f"score_weight_{k}"
            if key in cfg:
                weights[k] = float(cfg[key])
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        return weights
    except Exception as e:
        logger.warning("スコア重み読み込みエラー（デフォルト使用）: %s", e)
        return dict(SCORE_WEIGHTS)

ELEMENT_KEYS = ["fire", "earth", "air", "water"]
AURA_KEYS    = ["intuition", "clarity", "stability", "vitality",
                 "protection", "love", "expression", "courage"]


# ===== 商品プロファイル計算 =====

def _calc_product_profile(product: ProductEntry) -> dict:
    """
    商品の石構成と組み合わせマスタから、商品全体のプロファイルを計算する。
    粒数は影響させず、役割×サイズの重みで合成する。
    """
    element_vec: dict[str, float] = {k: 0.0 for k in ELEMENT_KEYS}
    aura_vec:    dict[str, float] = {k: 0.0 for k in AURA_KEYS}
    theme_tags:  set[str]         = set()
    worry_tags:  set[str]         = set()
    total_weight = 0.0

    parts = product["parts"]

    # --- 石単体の寄与 ---
    for part in parts:
        stone = get_stone(part["stone_id"])
        if stone is None:
            logger.warning("stone_id not found: %s", part["stone_id"])
            continue

        rw = get_role_weight(part["role"], part["size"]) * stone.get("weight", 1.0)

        for k in ELEMENT_KEYS:
            element_vec[k] += stone["element_profile"].get(k, 0.0) * rw
        for k in AURA_KEYS:
            aura_vec[k] += stone["aura_profile"].get(k, 0.0) * rw

        theme_tags.update(stone.get("theme_tags", []))
        worry_tags.update(stone.get("worry_tags", []))
        total_weight += rw

    # --- 組み合わせ効果の寄与 ---
    for (part_a, part_b) in combinations(parts, 2):
        effect = get_combination_effect(part_a["stone_id"], part_b["stone_id"])
        if effect is None:
            continue

        combo_rw = get_combination_role_weight(part_a["role"], part_b["role"])
        w = effect.get("weight", 1.0) * combo_rw

        for k in ELEMENT_KEYS:
            element_vec[k] += effect["element_bonus"].get(k, 0.0) * w
        for k in AURA_KEYS:
            aura_vec[k] += effect["aura_bonus"].get(k, 0.0) * w

        theme_tags.update(effect.get("theme_tags", []))
        worry_tags.update(effect.get("worry_tags", []))

    # --- 正規化（最大値を1.0に揃える） ---
    if total_weight > 0:
        max_e = max(element_vec.values()) or 1.0
        element_vec = {k: v / max_e for k, v in element_vec.items()}
        max_a = max(aura_vec.values()) or 1.0
        aura_vec = {k: v / max_a for k, v in aura_vec.items()}

    return {
        "element": element_vec,
        "aura":    aura_vec,
        "theme_tags": list(theme_tags),
        "worry_tags": list(worry_tags),
    }


# ===== ユーザープロファイル =====

def build_user_profile(
    element_lack: dict[str, float],
    aura_need:    dict[str, float],
    theme_tags:   list[str],
    worry_tags:   list[str],
) -> dict:
    """
    診断結果からユーザーのプロファイルを生成する。
    element_lack: 不足エレメント（0.0〜1.0）
    aura_need:    必要なオーラ（0.0〜1.0）
    theme_tags:   テーマ文字列リスト
    worry_tags:   悩みキーワードリスト
    """
    return {
        "element": element_lack,
        "aura":    aura_need,
        "theme_tags": theme_tags,
        "worry_tags": worry_tags,
    }


# ===== スコア計算 =====

def _cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    """2つのベクトルのコサイン類似度を計算する（0.0〜1.0）"""
    keys = set(vec_a) | set(vec_b)
    dot   = sum(vec_a.get(k, 0.0) * vec_b.get(k, 0.0) for k in keys)
    norm_a = sum(v ** 2 for v in vec_a.values()) ** 0.5
    norm_b = sum(v ** 2 for v in vec_b.values()) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _tag_overlap_score(user_tags: list[str], product_tags: list[str]) -> float:
    """タグの一致率を計算する（0.0〜1.0）"""
    if not user_tags or not product_tags:
        return 0.0
    user_set    = set(user_tags)
    product_set = set(product_tags)
    overlap = len(user_set & product_set)
    return overlap / len(user_set)


def _score_product(user_profile: dict, product_profile: dict) -> dict:
    """商品とユーザープロファイルの一致率を計算する（合計と内訳を返す）"""
    e_score = _cosine_similarity(user_profile["element"], product_profile["element"])
    a_score = _cosine_similarity(user_profile["aura"],    product_profile["aura"])
    t_score = _tag_overlap_score(user_profile["theme_tags"], product_profile["theme_tags"])
    w_score = _tag_overlap_score(user_profile["worry_tags"], product_profile["worry_tags"])

    w = get_score_weights()
    total = (
        e_score * w["element"] +
        a_score * w["aura"]    +
        t_score * w["theme"]   +
        w_score * w["worry"]
    )
    return {
        "total":   round(total * 100, 1),
        "element": round(e_score * 100, 1),
        "aura":    round(a_score * 100, 1),
        "theme":   round(t_score * 100, 1),
        "worry":   round(w_score * 100, 1),
    }


# ===== 推薦理由生成 =====

def _build_reason(user_profile: dict, product_profile: dict, product: ProductEntry) -> str:
    """推薦理由の簡潔なテキストを生成する"""
    parts = product["parts"]
    stone_names = []
    for part in parts:
        stone = get_stone(part["stone_id"])
        if stone:
            stone_names.append(stone["stone_name"])

    # 一致したテーマタグ
    matched_themes = list(
        set(user_profile.get("theme_tags", [])) &
        set(product_profile.get("theme_tags", []))
    )
    # 一致した悩みタグ
    matched_worries = list(
        set(user_profile.get("worry_tags", [])) &
        set(product_profile.get("worry_tags", []))
    )

    reason_parts = []
    if stone_names:
        reason_parts.append(f"使用石：{' × '.join(stone_names)}")
    if matched_themes:
        reason_parts.append(f"テーマ：{' / '.join(matched_themes[:3])}")
    if matched_worries:
        reason_parts.append(f"悩み：{' / '.join(matched_worries[:2])}")

    return "　".join(reason_parts) if reason_parts else "あなたの星読みに共鳴する構成です"


# ===== メイン推薦関数 =====

def recommend_products(
    user_profile: dict,
    top_n: int = 3,
) -> list[dict]:
    """
    ユーザープロファイルに対して一致率上位3商品を返す。

    戻り値の形式:
    [
      {
        "rank": 1,
        "score": 87.4,
        "woo_product_id": 1203,
        "sku": "bracelet-lapis-gray",
        "recommendation_reason": "...",
        "stones": ["ラピスラズリ", "水晶"],
      },
      ...
    ]
    """
    try:
        from api.utils_sheet import get_config
        cfg = get_config()
    except Exception:
        cfg = {}
    enabled_products = get_enabled_products(cfg)
    results = []

    for product in enabled_products:
        try:
            product_profile = _calc_product_profile(product)
            score_data = _score_product(user_profile, product_profile)
            # priority_weight による補正（最大±5点）
            total = min(100.0, score_data["total"] * product.get("priority_weight", 1.0))

            stone_names = []
            stone_colors = []  # 石ごとの代表色（color_tagsの先頭）
            for part in product["parts"]:
                stone = get_stone(part["stone_id"])
                if stone:
                    stone_names.append(stone["stone_name"])
                    tags = stone.get("color_tags", [])
                    stone_colors.append(tags[0] if tags else "")

            reason = _build_reason(user_profile, product_profile, product)

            results.append({
                "score":              total,
                "score_breakdown": {
                    "element": score_data["element"],
                    "aura":    score_data["aura"],
                    "theme":   score_data["theme"],
                    "worry":   score_data["worry"],
                },
                "woo_product_id":     product["woo_product_id"],
                "sku":                product["sku"],
                "recommendation_reason": reason,
                "stones":             stone_names,
                "stone_colors":       stone_colors,
            })
        except Exception as e:
            logger.error("商品スコア計算エラー woo_product_id=%s: %s",
                         product.get("woo_product_id"), e)
            continue

    # スコア降順ソート → 上位N件
    results.sort(key=lambda x: x["score"], reverse=True)
    top = results[:top_n]

    for i, item in enumerate(top, start=1):
        item["rank"] = i

    return top
