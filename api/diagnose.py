from flask import request, jsonify
from api.utils_perplexity import generate_bracelet_reading
from api.utils_order import build_order_summary
from api.utils_sheet import add_diagnosis
from datetime import datetime
import uuid
import json
import traceback
import sys
import time


def diagnose():
    """
    第1フェーズ：無料版（石の名前だけ返す）
    """
    start_time = time.time()
    print("--- Diagnose Request Started (Phase 1: Free Version) ---")

    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"error": "Empty request body"}), 400

        print(f"Received data: {data}")

        # =============================
        # 1. AI実行
        # =============================
        result = generate_bracelet_reading(data)

        if not isinstance(result, dict):
            return jsonify({"error": "Invalid AI response"}), 500

        # =============================
        # 2. 石を1種類に強制
        # =============================
        stones_for_user = result.get("stones_for_user", [])
        if not stones_for_user:
            return jsonify({"error": "No stone generated"}), 500

        main_stone = stones_for_user[0]   # ← 必ず1つだけ使用
        stone_name = main_stone.get("name", "不明")

        # =============================
        # 3. 商品スラッグ固定マッピング
        # =============================
        STONE_PRODUCT_MAP = {
            "アメジスト": "top-amethyst",
            "ローズクォーツ": "top-rose",
            "シトリン": "top-citrine",
            "ガーネット": "top-garnet",
            "アクアマリン": "top-aquamarine",
            "ムーンストーン": "top-moonstone",
            "タイガーアイ": "top-tigereye",
            "アベンチュリン": "top-aventurine",
            "ラピスラズリ": "top-lapis",
            "水晶": "top-crystal"
        }

        product_slug = STONE_PRODUCT_MAP.get(stone_name, "top-crystal")

        # =============================
        # 4. 診断ID生成
        # =============================
        diagnosis_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()

        # =============================
        # 5. full_result（Sheets保存用）
        # =============================
        full_result = {
            "diagnosis_id": diagnosis_id,
            "created_at": created_at,
            "stone_name": stone_name,
            "element_lack": result.get("element_lack", ""),
            "horoscope_full": result.get("horoscope_full", ""),
            "past": result.get("past", ""),
            "present": result.get("present", ""),
            "future": result.get("future", ""),
            "element_detail": result.get("element_detail", ""),
            "oracle_name": result.get("oracle_card", {}).get("name", ""),
            "oracle_position": result.get("oracle_card", {}).get("position", ""),
            "product_slug": product_slug
        }

        # =============================
        # 6. Sheets保存
        # =============================
        try:
            add_diagnosis(full_result)
        except Exception as sheet_err:
            print("Sheet save error:", sheet_err)

        # =============================
        # 7. 無料返却データ（短縮版）
        # =============================
        free_result = {
            "diagnosis_id": diagnosis_id,
            "stone_name": stone_name,
            "short_message": f"今のあなたに必要なのは『{stone_name}』です。",
            "cta": "詳しい鑑定結果を見るにはLINE登録へ"
        }

        elapsed_time = time.time() - start_time
        print(f"Diagnose finished in {elapsed_time:.2f}s")

        return jsonify(free_result)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500


def build_bracelet():
    """
    第2フェーズ：石候補 + 手首サイズ + ビーズサイズ + デザイン選択から、完成ブレスレットを生成
    """
    start_time = time.time()
    print("--- Build Bracelet Request Started (Phase 2: Size & Design) ---")

    try:
        # 1. リクエストボディの取得
        data = request.get_json(force=True, silent=True) or {}

        print(f"Received bracelet data: {data}")

        # 2. パラメータ取得
        diagnosis_id = data.get("diagnosis_id", str(uuid.uuid4())[:8])
        stones_for_user = result.get("stones_for_user") or [
            {"name": "水晶", "reason": "AIが石を返さなかったためデフォルト"}
        ]

        try:
            wrist_inner_cm = float(data.get("wrist_inner_cm") or 15.0)
            bead_size_mm = int(data.get("bead_size_mm") or 8)
        except ValueError as ve:
            print(f"Value Error in dimensions: {ve}")
            wrist_inner_cm = 15.0
            bead_size_mm = 8

        design_style = data.get("design_style", "おまかせ")  # デザインスタイル

        # 3. ブレスレットデザイン生成
        bracelet_design = build_bracelet_design(
            stones_for_user, wrist_inner_cm, bead_size_mm, design_style)
        stones = bracelet_design["stones"]
        design_text = bracelet_design["design_text"]

        # 4. 「あなたを導く石たち」というカスタム注文内容を生成
        order_summary = generate_stone_summary(
            stones, wrist_inner_cm, bead_size_mm, design_style)

        # 処理時間の計測ログ
        elapsed_time = time.time() - start_time
        print(f"Build bracelet finished in {elapsed_time:.2f} seconds.")

        # 5. 成功レスポンス
        response_data = {
            "diagnosis_id": diagnosis_id,
            "phase": "bracelet_complete",
            "design_text": design_text,
            "stones": stones,
            "order_summary": order_summary,
            "wrist_inner_cm": wrist_inner_cm,
            "bead_size_mm": bead_size_mm,
            "design_style": design_style
        }

        return jsonify(response_data)

    except Exception as e:
        print(f"Bracelet Build Error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "error": "Bracelet Build Error",
            "message": str(e),
            "code": "BRACELET_ERROR"
        }), 500


def build_bracelet_design(stones_for_user: list, wrist_inner_cm: float, bead_size_mm: int, design_style: str) -> dict:
    """
    石候補 + サイズ + デザインスタイルから、ブレスレットの個数・配置を決める
    デザイン選択によって石の選択を変える：
    - 1色 → 1番の石のみ
    - 2色 → 1番と2番の石を同じサイズで
    - トップ → 1番の石を1つ、2番目の石を周りに敷き詰める
    - おまかせ → 1番と2番で5:5のバランス
    """
    if not stones_for_user:
        return {
            "stones": [],
            "design_concept": "未指定",
            "design_text": "石の候補が取得できませんでした。"
        }

    # 1番・2番の石だけを使う
    main = stones_for_user[0]  # 一番おすすめ
    second = stones_for_user[1] if len(
        stones_for_user) > 1 else stones_for_user[0]  # 二番目（なければ同じ）

    # 必要な粒数をざっくり計算（ゴムの余裕を含む）
    bracelet_length_mm = wrist_inner_cm * 10 + 10
    total_bead_count = max(12, int(bracelet_length_mm / bead_size_mm))

    stones = []

    # デザインスタイルに応じた配置
    if design_style == "単色（シンプル）":
        # 1色：一番おすすめの石だけ
        stones.append({
            "name": main["name"],
            "reason": main["reason"],
            "count": total_bead_count,
            "position": "top"
        })

    elif design_style == "２色（混合）":
        # 2色：1番と2番の石を同じサイズで、6:4 くらいの配分
        main_count = int(total_bead_count * 0.6)
        second_count = total_bead_count - main_count

        stones.append({
            "name": main["name"],
            "reason": main["reason"],
            "count": main_count,
            "position": "top"
        })
        stones.append({
            "name": second["name"],
            "reason": second["reason"],
            "count": second_count,
            "position": "side"
        })

    elif design_style == "トップを入れる":
        # トップ：1番の石を1粒だけトップに、2番目の石を周りに敷き詰める
        surrounding_count = max(11, total_bead_count - 1)

        stones.append({
            "name": main["name"],
            "reason": main["reason"],
            "count": 1,
            "position": "accent"   # トップ
        })
        stones.append({
            "name": second["name"],
            "reason": second["reason"],
            "count": surrounding_count,
            "position": "top"      # 周囲を埋める石
        })

    else:  # おまかせ
        # デフォルトはバランス型：1番と2番を 5:5 くらい
        main_count = total_bead_count // 2
        second_count = total_bead_count - main_count

        stones.append({
            "name": main["name"],
            "reason": main["reason"],
            "count": main_count,
            "position": "top"
        })
        stones.append({
            "name": second["name"],
            "reason": second["reason"],
            "count": second_count,
            "position": "side"
        })

    design_concept = f"「{main['name']}」と「{second['name']}」で仕上げるブレス（デザイン：{design_style}）"

    design_text = generate_design_text(
        main, second, stones, design_style, wrist_inner_cm, bead_size_mm)

    return {
        "stones": stones,
        "design_concept": design_concept,
        "design_text": design_text,
        "sales_copy": f"あなたを導く {main['name']} ブレスレット"
    }


def generate_design_text(main_stone: dict, second_stone: dict, stones: list, design_style: str, wrist_inner_cm: float, bead_size_mm: int) -> str:
    """
    3段落＋小見出し付きのデザイン説明を生成（約3倍のボリューム）
    """
    stone_list = "、".join([s["name"] for s in stones[:3]])

    part1 = f"""
デザインコンセプト

このブレスレットのメインストーンとして選ばれた**{main_stone['name']}**は、あなたの悩みに最も共鳴する石です。{main_stone['reason']}

このメインストーンを中心に据えることで、日常的にあなたのエネルギーを整え、願いを現実へ導くサポートをしてくれます。毎日身に付けることで、石からのメッセージが無意識のうちにあなたの行動や選択に影響を与え、より良い方向へ導いてくれるでしょう。
"""

    part2 = f"""
サポートストーンの役割

メインストーンの力をさらに高めるために、**{second_stone['name']}**をサポートストーンとして選びました。この石はメインストーンの作用を強化し、より多角的にあなたをサポートします。

複数の石を組み合わせることで、単体の石よりも何倍もの相乗効果が生まれます。各石のエネルギーが調和することで、より深い癒しと導きを体験することができるようになります。
"""

    part3 = f"""
日常での使い方と効果

内径**{wrist_inner_cm}cm**、ビーズサイズ**{bead_size_mm}mm**に調整したこのブレスレットは、どんな場面でも無理なく身に付けることができます。仕事中、日常生活、瞑想時、就寝時まで、24時間あなたのそばに置いて、石からのエネルギーを受け取ってください。

デザインスタイル「**{design_style}**」で仕上げたこのブレスレットは、{get_style_description(design_style)}という特徴があります。見た目の美しさと、石からの力強いサポートを兼ね備えた、あなただけの運命を変えるお守りとなるでしょう。
"""

    return part1 + part2 + part3


def get_style_description(style: str) -> str:
    """デザインスタイルの説明"""
    descriptions = {
        "単色（シンプル）": "シンプルで洗練された見た目が特徴で、すべてを同じ石で統一することで、そのエネルギーに全身を包み込ませます",
        "２色（混合）": "メイン石とサポート石の2色で彩られ、バランスの取れた見た目と、複数の石からの相乗効果を同時に享受できます",
        "トップを入れる": "ブレスレットの中央に特別なトップストーンを配置し、より目立たせることで、石からのパワーが一層強く作用します",
        "おまかせ": "石たちの個性が最も活かされたデザインで、複数の石がそれぞれのリズムを奏でながらあなたをサポートします"
    }
    return descriptions.get(style, "あなたのために最適な配置で仕上げています")


def generate_stone_summary(stones: list, wrist_inner_cm: float, bead_size_mm: int, design_style: str) -> str:
    """
    「あなたを導く石たち」というカスタマイズされた注文内容を生成
    """
    summary = f"""
あなたを導く石たち

■ ブレスレットサイズ
  • 内径：{wrist_inner_cm}cm
  • ビーズサイズ：{bead_size_mm}mm

■ デザインスタイル
  {design_style}

■ 使用する石と個数
"""

    for stone in stones:
        summary += f"  • {stone['name']}：{stone['count']}個（{stone['position']}）\n"

    total_beads = sum(s['count'] for s in stones)
    summary += f"\n■ ビーズ総数：{total_beads}個\n"

    return summary
