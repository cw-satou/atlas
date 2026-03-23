"""診断モジュール

占い診断の2つのフェーズを実装する:
- Phase 1 (diagnose): 不足エレメントと代表石の選定
- Phase 2 (build_bracelet): 手首サイズ・デザインに基づくブレスレット生成
"""

import logging
import time
import traceback
import uuid
from datetime import datetime

from flask import request, jsonify

from api.utils_perplexity import generate_bracelet_reading
from api.utils_order import build_order_summary
from api.utils_sheet import add_diagnosis, format_stones, update_diagnosis

logger = logging.getLogger(__name__)

# エレメント → 代表石のマッピング
ELEMENT_STONE_MAP = {
    "火": "ガーネット",
    "地": "タイガーアイ",
    "風": "ラピスラズリ",
    "水": "アクアマリン",
}

# 石 → 商品スラッグのマッピング
STONE_PRODUCT_MAP = {
    "ガーネット": "top-garnet",
    "タイガーアイ": "top-tiger-eye",
    "ラピスラズリ": "top-lapis",
    "アクアマリン": "top-aquamarine",
    "水晶": "top-crystal",
}

# 誕生石マッピング
BIRTHSTONE_MAP = {
    1: ("ガーネット", "情熱と生命力を象徴する石"),
    2: ("アメジスト", "精神を落ち着かせ直感を高める石"),
    3: ("アクアマリン", "心を穏やかにする石"),
    4: ("水晶", "浄化と調和の石"),
    5: ("エメラルド", "愛と再生の石"),
    6: ("ムーンストーン", "感情と直感の石"),
    7: ("ルビー", "情熱と守護の石"),
    8: ("ペリドット", "希望とポジティブな変化の石"),
    9: ("サファイア", "知性と洞察の石"),
    10: ("オパール", "創造性と自由の石"),
    11: ("トパーズ", "成功と希望の石"),
    12: ("ターコイズ", "守護と旅の石"),
}


def get_birthstone_from_birth(birth_info: dict) -> dict:
    """生年月日から誕生石候補を返す

    Args:
        birth_info: {"date": "YYYY-MM-DD", ...} 形式の辞書

    Returns:
        {"name": "石名", "reason": "説明"} の辞書
    """
    date_str = (birth_info or {}).get("date")
    if not date_str:
        return {"name": "水晶", "reason": "どの月とも相性がよい万能の石です。"}

    try:
        month = int(date_str.split("-")[1])
    except (IndexError, ValueError):
        return {"name": "水晶", "reason": "どの月とも相性がよい万能の石です。"}

    name, reason = BIRTHSTONE_MAP.get(month, ("水晶", "調和の石"))
    return {"name": name, "reason": f"{month}月生まれのあなたを守る誕生石です。{reason}"}


def diagnose():
    """第1フェーズ：不足エレメントと代表石1種類を返す"""
    start_time = time.time()
    logger.info("診断リクエスト開始（Phase 1: エレメント＆メインストーン）")

    try:
        req = request.get_json(force=True, silent=True)
        if not req:
            return jsonify({"error": "リクエストボディが空です"}), 400

        diagnosis_id = str(uuid.uuid4())
        line_user_id = req.get("line_user_id")

        # AI鑑定実行
        result = generate_bracelet_reading(req)
        if not isinstance(result, dict):
            return jsonify({"error": "AIレスポンスが不正です"}), 500

        if result.get("error"):
            logger.error(f"AI鑑定エラー: {result['error']}")
            return jsonify({"error": result["error"]}), 500

        # 不足エレメントと代表石の決定
        element_lack = result.get("element_lack", "")
        stone_name = ELEMENT_STONE_MAP.get(element_lack, "水晶")
        product_slug = STONE_PRODUCT_MAP.get(stone_name, "top-crystal")
        created_at = datetime.utcnow().isoformat()

        stones_for_user = [{
            "name": stone_name,
            "reason": f"不足している「{element_lack}」のエレメントを補い、あなたのバランスを整える石です。",
        }]

        # スプレッドシートに保存
        log_data = {
            "diagnosis_id": diagnosis_id,
            "created_at": created_at,
            "stone_name": stone_name,
            "element_lack": element_lack,
            "product_slug": product_slug,
            "horoscope_full": result.get("destiny_map", ""),
            "past": result.get("past", ""),
            "present_future": result.get("present_future", ""),
            "element_detail": result.get("element_diagnosis", ""),
            "oracle_name": result.get("oracle_card", {}).get("name", ""),
            "oracle_position": result.get("oracle_card", {}).get("position", ""),
            "stones": "",
            "user_line_id": line_user_id or "",
        }

        try:
            add_diagnosis(log_data)
        except Exception as e:
            logger.error(f"スプレッドシート保存エラー: {e}")

        # レスポンス構築
        full_response = {
            **result,
            "line_user_id": line_user_id,
            "diagnosis_id": diagnosis_id,
            "element_lack": element_lack,
            "stone_name": stone_name,
            "product_slug": product_slug,
            "oraclecardname": result.get("oracle_card", {}).get("name", ""),
            "short_message": result.get("short_message") or (
                f"今のあなたに不足しているのは「{element_lack}」のエレメント。"
                f"そのバランスを整える代表的な石が『{stone_name}』です。"
            ),
            "stones_for_user": result.get("stones_for_user") or stones_for_user,
        }

        elapsed = time.time() - start_time
        logger.info(f"診断完了: {elapsed:.2f}秒")

        return jsonify(full_response)

    except Exception as e:
        logger.exception("診断処理中にエラーが発生")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e),
        }), 500


def build_bracelet():
    """第2フェーズ：石候補＋手首サイズ＋デザインからブレスレットを生成する"""
    start_time = time.time()
    logger.info("ブレスレット生成リクエスト開始（Phase 2: サイズ＆デザイン）")

    try:
        data = request.get_json(force=True, silent=True) or {}

        diagnosis_id = data.get("diagnosis_id", str(uuid.uuid4())[:8])

        stones_for_user = data.get("stones_for_user") or [
            {"name": "水晶", "reason": "AIが石を返さなかったためデフォルト"}
        ]

        try:
            wrist_inner_cm = float(data.get("wrist_inner_cm") or 15.0)
        except (ValueError, TypeError):
            wrist_inner_cm = 15.0

        bead_size_mm = 8
        bracelet_type = data.get("bracelet_type") or "element_top_only"

        # ブレスレットデザイン生成
        bracelet_design = _build_bracelet_design(
            stones_for_user, wrist_inner_cm, bead_size_mm, bracelet_type, data
        )
        stones = bracelet_design["stones"]
        design_text = bracelet_design["design_text"]

        # 注文サマリー生成
        order_summary = build_order_summary(
            {"stones": stones}, wrist_inner_cm, bead_size_mm
        )

        # スプレッドシート更新
        stone_counts = {s["name"]: s["count"] for s in stones}
        stones_str = format_stones(stone_counts)
        try:
            update_diagnosis(diagnosis_id, stones_str, "")
        except Exception as e:
            logger.error(f"診断更新エラー: {e}")

        elapsed = time.time() - start_time
        logger.info(f"ブレスレット生成完了: {elapsed:.2f}秒")

        return jsonify({
            "diagnosis_id": diagnosis_id,
            "phase": "bracelet_complete",
            "design_text": design_text,
            "stones": stones,
            "order_summary": order_summary,
            "wrist_inner_cm": wrist_inner_cm,
            "bead_size_mm": bead_size_mm,
            "bracelet_type": bracelet_type,
        })

    except Exception as e:
        logger.exception("ブレスレット生成エラー")
        return jsonify({
            "error": "Bracelet Build Error",
            "message": str(e),
        }), 500


def _build_bracelet_design(
    stones_for_user: list,
    wrist_inner_cm: float,
    bead_size_mm: int,
    bracelet_type: str,
    request_data: dict,
) -> dict:
    """ブレスレットデザインを構築する

    Args:
        stones_for_user: エレメント石の候補リスト
        wrist_inner_cm: 手首の内径（cm）
        bead_size_mm: ビーズサイズ（mm）
        bracelet_type: ブレスレットタイプ
        request_data: リクエスト全体のデータ

    Returns:
        stones, design_concept, design_text, sales_copy を含む辞書
    """
    if not stones_for_user:
        return {
            "stones": [],
            "design_concept": "未指定",
            "design_text": "石の候補が取得できませんでした。",
        }

    element_stone = stones_for_user[0]
    birth_info = (request_data or {}).get("birth") or {}
    birth_stone = get_birthstone_from_birth(birth_info)

    bracelet_length_mm = wrist_inner_cm * 10 + 10
    total_bead_count = max(12, int(bracelet_length_mm / bead_size_mm))

    stones = []

    if bracelet_type == "birth_top_element_side":
        surrounding_count = max(11, total_bead_count - 1)
        stones.append({
            "name": birth_stone["name"],
            "reason": birth_stone["reason"],
            "count": 1,
            "position": "accent",
        })
        stones.append({
            "name": element_stone["name"],
            "reason": element_stone["reason"],
            "count": surrounding_count,
            "position": "side",
        })
        design_concept = (
            f"誕生石「{birth_stone['name']}」をトップに、"
            f"エレメントを整える石「{element_stone['name']}」で全体を包み込むブレスレット"
        )
    else:
        # element_top_only またはフォールバック
        stones.append({
            "name": element_stone["name"],
            "reason": element_stone["reason"],
            "count": total_bead_count,
            "position": "top",
        })
        if bracelet_type == "element_top_only":
            design_concept = (
                f"不足しているエレメントを集中的に補う、"
                f"{element_stone['name']}だけで仕上げたシンプルなブレスレット"
            )
        else:
            design_concept = f"{element_stone['name']}をメインにしたブレスレット"

    design_text = _generate_design_text(
        birth_stone, element_stone, bracelet_type,
        wrist_inner_cm, bead_size_mm, design_concept,
    )

    return {
        "stones": stones,
        "design_concept": design_concept,
        "design_text": design_text,
        "sales_copy": f"あなたを導く {element_stone['name']} ブレスレット",
    }


def _generate_design_text(
    birth_stone: dict,
    element_stone: dict,
    bracelet_type: str,
    wrist_inner_cm: float,
    bead_size_mm: int,
    design_concept: str,
) -> str:
    """デザイン説明テキストを生成する"""
    if bracelet_type == "birth_top_element_side":
        style_desc = (
            "誕生石をブレスレットの中心に据え、その周りをエレメント石で囲むことで、"
            "『本来のあなた』と『今必要なエネルギー』の両方を同時に引き出すデザインです。"
        )
    else:
        style_desc = (
            "不足しているエレメントに特化したシンプルな構成で、"
            "余計な要素をそぎ落とし、石の持つ力をダイレクトに感じやすいデザインです。"
        )

    part1 = (
        f"\nデザインコンセプト\n\n"
        f"このブレスレットの核となる石は、**{element_stone['name']}**です。"
        f"{element_stone['reason']}\n{design_concept}\n"
    )

    if bracelet_type == "birth_top_element_side":
        part2 = (
            f"\n誕生石とエレメント石のバランス\n\n"
            f"トップには、あなたの生まれ持った流れを象徴する"
            f"**{birth_stone['name']}**を一粒だけ配置しました。"
            f"{birth_stone['reason']}\n"
            f"その周りを取り囲むように配置された**{element_stone['name']}**が、"
            f"今のあなたの状態に合わせて不足しているエレメントを丁寧に補っていきます。\n"
        )
    else:
        part2 = (
            f"\nエレメントに特化したシンプルデザイン\n\n"
            f"ブレスレット全体を**{element_stone['name']}**のみで構成することで、"
            f"テーマを一つに絞り、エネルギーの方向性をクリアにしました。\n"
            f"迷いや雑音を減らし、「今の自分にとって何が大事か」を"
            f"見つめ直すサポートをしてくれます。\n"
        )

    part3 = (
        f"\n日常での使い方と効果\n\n"
        f"内径**{wrist_inner_cm}cm**、ビーズサイズ**{bead_size_mm}mm**で仕上げているため、"
        f"日常使いしやすく、さりげなく身につけていられます。\n"
        f"{style_desc}\n"
        f"ふと心が揺れたときや、選択に迷ったときは、ブレスレットにそっと触れて"
        f"深呼吸をしてみてください。今のあなたに必要な方向へ、"
        f"すこしずつ舵を切る手助けをしてくれるはずです。\n"
    )

    return part1 + part2 + part3
