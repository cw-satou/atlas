"""診断モジュール

2フェーズ診断を実装する:
- Phase 1 (diagnose): ホロスコープ診断 → マッチングエンジンで上位3商品を提案
- Phase 2 (build_bracelet): 手首サイズ・デザインに基づくブレスレット注文情報生成
"""

import logging
import time
import uuid
from datetime import datetime, timezone

from flask import request, jsonify

from api.utils_perplexity import (
    generate_bracelet_reading,
    calculate_chart,
    build_chart_data,
)
from api.utils_order import build_order_summary
from api.utils_sheet import add_diagnosis, format_stones, update_diagnosis
from api.utils_geocode import geocode
from api.matching import recommend_products, build_user_profile
from api.utils_woo import fetch_woo_products

logger = logging.getLogger(__name__)

# ===== 悩み → テーマタグ・悩みタグ変換 =====

CONCERN_THEME_MAP: dict[str, list[str]] = {
    "恋愛":     ["愛情", "自己愛", "調和"],
    "仕事":     ["行動力", "目標達成", "実現力"],
    "金運":     ["金運", "豊かさ", "実現力"],
    "健康":     ["癒し", "安定", "活力"],
    "人間関係": ["調和", "コミュニケーション", "保護"],
    "その他":   ["直感", "自己理解", "前進"],
}

CONCERN_WORRY_MAP: dict[str, list[str]] = {
    "恋愛":     ["恋愛", "孤独感", "自己否定"],
    "仕事":     ["仕事", "踏み出せない", "停滞感"],
    "金運":     ["金運", "停滞感", "ネガティブ思考"],
    "健康":     ["ストレス", "疲労感", "何となく不調"],
    "人間関係": ["人間関係", "感情の揺れ", "他人の影響を受けやすい"],
    "その他":   ["迷い", "不安", "方向性"],
}

# エレメント名の英語→英語正規化（horoscope側は "wind"、matching側は "air" を使用）
ELEMENT_NORMALIZE = {"wind": "air"}

# problem テキストのキーワード → worry_tags / theme_tags マッピング
# キーワードがテキストに含まれていれば対応するタグを追加する
PROBLEM_KEYWORD_MAP: list[tuple[list[str], list[str], list[str]]] = [
    # (検索キーワード, 追加worry_tags, 追加theme_tags)
    (["仕事", "職場", "会社", "転職", "キャリア", "昇進", "副業"],
     ["仕事", "停滞感", "踏み出せない"], ["行動力", "目標達成", "実現力"]),
    (["お金", "金銭", "収入", "給料", "貯金", "節約", "投資", "お財布", "財布", "金欠"],
     ["金運", "停滞感"], ["金運", "豊かさ"]),
    (["恋愛", "恋", "好き", "彼氏", "彼女", "結婚", "夫", "妻", "パートナー",
      "浮気", "別れ", "片思い", "告白", "デート"],
     ["恋愛", "孤独感", "感情の揺れ"], ["愛情", "自己愛", "調和"]),
    (["健康", "体調", "疲れ", "疲労", "眠れない", "睡眠", "病気", "不調", "だるい"],
     ["疲労感", "眠れない", "何となく不調"], ["癒し", "活力"]),
    (["不安", "心配", "怖い", "恐い", "こわい"],
     ["不安", "焦り"], ["精神統一", "安定"]),
    (["ストレス", "プレッシャー", "追い詰め"],
     ["ストレス", "焦り"], ["癒し", "精神統一"]),
    (["人間関係", "人付き合い", "友達", "友人", "家族", "上司", "部下", "同僚", "職場の人"],
     ["人間関係", "感情の揺れ", "他人の影響を受けやすい"], ["調和", "コミュニケーション"]),
    (["孤独", "ひとり", "一人", "孤立", "寂しい"],
     ["孤独感", "自己否定"], ["愛情", "自己愛"]),
    (["自信", "自己肯定", "自分を信じ", "自分が嫌"],
     ["自信不足", "自己否定"], ["自己表現", "行動力"]),
    (["やる気", "モチベーション", "元気がない", "無気力", "だらだら"],
     ["やる気がでない", "停滞感"], ["行動力", "活力"]),
    (["迷い", "迷って", "どうすれば", "わからない", "決められない", "決断"],
     ["迷い", "方向性", "決断できない"], ["直感", "自己理解"]),
    (["変わりたい", "変化", "前進", "踏み出", "一歩"],
     ["変化への恐れ", "踏み出せない"], ["変容", "前進"]),
]


def _extract_tags_from_problem(problem: str) -> tuple[list[str], list[str]]:
    """problem テキストをキーワードスキャンして worry_tags / theme_tags を抽出する"""
    extra_worry: list[str] = []
    extra_theme: list[str] = []
    for keywords, worry, theme in PROBLEM_KEYWORD_MAP:
        if any(kw in problem for kw in keywords):
            extra_worry.extend(worry)
            extra_theme.extend(theme)
    return list(dict.fromkeys(extra_worry)), list(dict.fromkeys(extra_theme))


def _build_user_profile_from_chart(
    chart_info: dict,
    concerns: list[str],
    problem: str = "",
) -> dict:
    """
    ホロスコープ情報・悩みカテゴリ・problem テキストからユーザープロファイルを生成する。

    不足エレメントを補いたいベクトルに変換し、
    悩みカテゴリと problem テキストのキーワードからテーマ・悩みタグを生成する。
    """
    balance = chart_info.get("element_balance") or {
        "fire": chart_info.get("fire", 1),
        "earth": chart_info.get("earth", 1),
        "wind": chart_info.get("wind", 1),
        "water": chart_info.get("water", 1),
    }

    # エレメントバランスを正規化し、少ない方を高くする（補いたいエレメント）
    total = sum(balance.values()) or 4
    element_lack: dict[str, float] = {}
    for raw_key, count in balance.items():
        normalized_key = ELEMENT_NORMALIZE.get(raw_key, raw_key)
        # 少ないほど値が高くなるよう反転
        element_lack[normalized_key] = max(0.0, 1.0 - (count / total))

    # 悩みカテゴリからタグを収集
    theme_tags: list[str] = []
    worry_tags: list[str] = []
    for concern in (concerns or []):
        theme_tags.extend(CONCERN_THEME_MAP.get(concern, []))
        worry_tags.extend(CONCERN_WORRY_MAP.get(concern, []))

    # problem テキストのキーワードからタグを追加（入力内容を優先反映）
    if problem:
        extra_worry, extra_theme = _extract_tags_from_problem(problem)
        # problem 由来タグを先頭に追加してマッチング重みを高める
        worry_tags = extra_worry + worry_tags
        theme_tags = extra_theme + theme_tags

    # 重複除去
    theme_tags = list(dict.fromkeys(theme_tags))
    worry_tags = list(dict.fromkeys(worry_tags))

    # 不足エレメントに対応したオーラニーズを生成
    aura_need = _element_to_aura_need(element_lack)

    return build_user_profile(
        element_lack=element_lack,
        aura_need=aura_need,
        theme_tags=theme_tags,
        worry_tags=worry_tags,
    )


def _element_to_aura_need(element_lack: dict[str, float]) -> dict[str, float]:
    """不足エレメントからオーラの必要度を推定する"""
    # エレメントとオーラの大まかな対応
    ELEMENT_AURA_MAP = {
        "fire":  {"vitality": 0.8, "courage": 0.7, "expression": 0.6},
        "earth": {"stability": 0.8, "protection": 0.6, "clarity": 0.5},
        "air":   {"intuition": 0.8, "clarity": 0.7, "expression": 0.6},
        "water": {"love": 0.8, "intuition": 0.7, "stability": 0.5},
    }

    aura_need: dict[str, float] = {
        "intuition": 0.0, "clarity": 0.0, "stability": 0.0,
        "vitality": 0.0, "protection": 0.0, "love": 0.0,
        "expression": 0.0, "courage": 0.0,
    }

    for element, lack_val in element_lack.items():
        aura_weights = ELEMENT_AURA_MAP.get(element, {})
        for aura_key, weight in aura_weights.items():
            aura_need[aura_key] = min(1.0, aura_need[aura_key] + weight * lack_val)

    return aura_need


# ===== Phase 1: 診断＆商品提案 =====

def diagnose():
    """Phase 1: ホロスコープ診断 → マッチングで上位3商品を提案"""
    start_time = time.time()
    logger.info("診断リクエスト開始（Phase 1）")

    try:
        req = request.get_json(force=True, silent=True)
        if not req:
            return jsonify({"error": "リクエストボディが空です"}), 400

        diagnosis_id = str(uuid.uuid4())
        line_user_id = req.get("line_user_id")
        concerns = req.get("concerns") or []

        # ホロスコープ計算
        chart_data = None
        birth = req.get("birth", {})
        if birth.get("date") and birth.get("time"):
            try:
                lat, lon = geocode(birth.get("place", ""))
                chart_data = calculate_chart(birth["date"], birth["time"], lat, lon)
                if chart_data:
                    logger.info(
                        "ホロスコープ計算完了: sun=%s, moon=%s, asc=%s",
                        chart_data.get("sun"), chart_data.get("moon"), chart_data.get("asc"),
                    )
            except Exception as e:
                logger.warning("ホロスコープ計算エラー（デフォルト値を使用）: %s", e)

        chart_info = build_chart_data(req, chart_data)

        # AI診断文＋オラクルカード生成
        ai_result = generate_bracelet_reading(req, chart_data=chart_data)
        if not isinstance(ai_result, dict):
            return jsonify({"error": "AIレスポンスが不正です"}), 500
        if ai_result.get("error"):
            logger.error("AI診断エラー: %s", ai_result["error"])
            return jsonify({"error": ai_result["error"]}), 500

        # ユーザープロファイル構築（problem テキストも反映）
        problem_text = req.get("problem", "") or ""
        user_profile = _build_user_profile_from_chart(chart_info, concerns, problem_text)

        # マッチングエンジンで上位3商品を取得
        top_products = recommend_products(user_profile, top_n=3)

        # ブレスレット画像はutils_perplexity側で並列生成済み（ai_result["images"]["bracelet"]）
        rank1_bracelet_image: str | None = (ai_result.get("images") or {}).get("bracelet")

        # WooCommerceから商品詳細を取得して補完
        woo_ids = [p["woo_product_id"] for p in top_products]
        woo_details = fetch_woo_products(woo_ids)

        recommendations = []
        for product in top_products:
            pid = product["woo_product_id"]
            woo = woo_details.get(pid, {})
            is_rank1 = product["rank"] == 1
            recommendations.append({
                "rank":                   product["rank"],
                "score":                  product["score"],
                "woo_product_id":         pid,
                "sku":                    product.get("sku", ""),
                "product_name":           woo.get("name", ""),
                "price":                  woo.get("price", ""),
                "image_url":              woo.get("image_url", ""),
                # ランク1はGemini生成ブレスレット画像を優先、なければWooCommerce画像
                "generated_image_url":    rank1_bracelet_image if is_rank1 else None,
                "product_url":            woo.get("product_url", ""),
                "stones":                 product.get("stones", []),
                "recommendation_reason":  product.get("recommendation_reason", ""),
                "oracle_card":            ai_result.get("oracle_card"),
                "diagnosis_message":      ai_result.get("stone_support_message", ""),
            })

        # スプレッドシートに診断ログ保存
        created_at = datetime.now(timezone.utc).isoformat()
        log_data = {
            "diagnosis_id":   diagnosis_id,
            "created_at":     created_at,
            "stone_name":     ", ".join(r["stones"][0] for r in recommendations if r["stones"]),
            "element_lack":   chart_info.get("element_lack", ""),
            "horoscope_full": ai_result.get("destiny_map", ""),
            "past":           ai_result.get("past", ""),
            "present_future": ai_result.get("present_future", ""),
            "element_detail": ai_result.get("element_diagnosis", ""),
            "oracle_name":    (ai_result.get("oracle_card") or {}).get("name", ""),
            "oracle_position": (ai_result.get("oracle_card") or {}).get("position", ""),
            "stones":         "",
            "product_slug":   recommendations[0]["sku"] if recommendations else "",
            "user_line_id":   line_user_id or "",
        }

        sheets_error = None
        try:
            add_diagnosis(log_data)
            logger.info("診断ログ保存完了: diagnosis_id=%s", diagnosis_id)
        except Exception as e:
            sheets_error = str(e)
            logger.error("スプレッドシート保存エラー: %s", e)

        elapsed = time.time() - start_time
        logger.info("診断完了: %.2f秒", elapsed)

        response = {
            "diagnosis_id":         diagnosis_id,
            "recommendations":      recommendations,
            "stone_name":           ai_result.get("stone_name", ""),
            "destiny_map":          ai_result.get("destiny_map", ""),
            "past":                 ai_result.get("past", ""),
            "present_future":       ai_result.get("present_future", ""),
            "element_diagnosis":    ai_result.get("element_diagnosis", ""),
            "bracelet_proposal":    ai_result.get("bracelet_proposal", ""),
            "stone_support_message": ai_result.get("stone_support_message", ""),
            "affirmation":          ai_result.get("affirmation", ""),
            "lucky_color":          ai_result.get("lucky_color", ""),
            "daily_advice":         ai_result.get("daily_advice", ""),
            "oracle_card":          ai_result.get("oracle_card"),
            "oracle_message":       ai_result.get("oracle_message", ""),
            # 画像: utils_perplexityが生成した画像 + rank1ブレスレット画像はrecommendationsに含む
            "images": {
                "destiny_scene":    (ai_result.get("images") or {}).get("destiny_scene"),
                "element_balance":  (ai_result.get("images") or {}).get("element_balance"),
                "bracelet":         rank1_bracelet_image or (ai_result.get("images") or {}).get("bracelet"),
            },
            "element_lack":         chart_info.get("element_lack", ""),
            "element_lack_ja":      chart_info.get("element_lack_ja", ""),
            "chart":                {
                "sun":     chart_info.get("sun_ja", ""),
                "moon":    chart_info.get("moon_ja", ""),
                "asc":     chart_info.get("asc_ja", ""),
                "mercury": chart_info.get("mercury_ja", ""),
                "venus":   chart_info.get("venus_ja", ""),
                "mars":    chart_info.get("mars_ja", ""),
            },
            "line_user_id":         line_user_id,
            # 保存エラーがあれば診断結果に含める（フロント側でログ確認用）
            **({"_sheets_error": sheets_error} if sheets_error else {}),
        }
        return jsonify(response)

    except Exception:
        logger.exception("診断処理中にエラーが発生")
        return jsonify({"error": "診断処理中にエラーが発生しました"}), 500


# ===== Phase 2: ブレスレット注文情報生成 =====

def build_bracelet():
    """Phase 2: 手首サイズ・デザインから注文情報を生成する"""
    start_time = time.time()
    logger.info("ブレスレット注文情報生成リクエスト開始（Phase 2）")

    try:
        data = request.get_json(force=True, silent=True) or {}
        diagnosis_id = data.get("diagnosis_id", str(uuid.uuid4())[:8])

        # 選択された商品の石構成
        woo_product_id = data.get("woo_product_id")
        stones_for_user = data.get("stones_for_user") or [
            {"name": "水晶", "reason": "選択情報がないためデフォルト"}
        ]

        try:
            wrist_inner_cm = float(data.get("wrist_inner_cm") or 15.0)
        except (ValueError, TypeError):
            wrist_inner_cm = 15.0

        bead_size_mm = 8
        bracelet_type = data.get("bracelet_type") or "standard"

        # 注文サマリー生成
        order_summary = build_order_summary(
            {"stones": stones_for_user}, wrist_inner_cm, bead_size_mm
        )

        # スプレッドシート更新
        stone_counts = {s["name"]: s.get("count", 1) for s in stones_for_user}
        stones_str = format_stones(stone_counts)
        try:
            update_diagnosis(diagnosis_id, stones_str, "")
        except Exception as e:
            logger.error("診断更新エラー: %s", e)

        elapsed = time.time() - start_time
        logger.info("ブレスレット注文情報生成完了: %.2f秒", elapsed)

        return jsonify({
            "diagnosis_id":    diagnosis_id,
            "phase":           "bracelet_complete",
            "woo_product_id":  woo_product_id,
            "stones":          stones_for_user,
            "order_summary":   order_summary,
            "wrist_inner_cm":  wrist_inner_cm,
            "bead_size_mm":    bead_size_mm,
            "bracelet_type":   bracelet_type,
        })

    except Exception:
        logger.exception("ブレスレット注文情報生成エラー")
        return jsonify({"error": "ブレスレット注文情報の生成中にエラーが発生しました"}), 500
