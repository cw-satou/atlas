from flask import request, jsonify
from api.utils_perplexity import generate_bracelet_reading
from api.utils_order import build_order_summary
from api.utils_sheet import add_diagnosis, format_stones, update_diagnosis
from datetime import datetime
from datetime import datetime
import uuid
import json
import traceback
import sys
import time
from api.utils_perplexity import generate_today_fortune  # 新しく作る

def diagnose(data, line_user_id=None):
    """
    第1フェーズ：不足エレメントと、そのエレメントを補う代表石1種類を返す
    """
    start_time = time.time()
    print("--- Diagnose Request Started (Phase 1: Element & Main Stone) ---")

    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"error": "Empty request body"}), 400
        
        diagnosis_id = str(uuid.uuid4())
        line_user_id = data.get("line_user_id")

        print(f"Received data: {data}")

        # 1. AI実行
        result = generate_bracelet_reading(data)
        if not isinstance(result, dict):
            return jsonify({"error": "Invalid AI response"}), 500

        # 2. 不足エレメント
        element_lack = result.get("element_lack", "")

        # 3. エレメント→石マッピング（今は1:1、将来ここを増やす）
        ELEMENT_STONE_MAP = {
            "火": "ガーネット",
            "地": "タイガーアイ",
            "風": "ラピスラズリ",
            "水": "アクアマリン",
            # 例: 増やすときは "火": ["ガーネット","カーネリアン"] などにして分岐
        }

        stone_name = ELEMENT_STONE_MAP.get(element_lack, "水晶")

        # 4. stones_for_user を「メイン石1つ」だけにしておく（将来は配列増やせる）
        stones_for_user = [{
            "name": stone_name,
            "reason": f"不足している「{element_lack}」のエレメントを補い、あなたのバランスを整える石です。"
        }]

        # 5. 診断ID生成
        diagnosis_id = data.get("diagnosis_id")

        if not diagnosis_id:
            return jsonify({"error": "diagnosis_id required"}), 400
        created_at = datetime.utcnow().isoformat()

        # 6. 結果をスプレッドシートに保存
        log_data = {
            "diagnosis_id": diagnosis_id,
            "created_at": created_at,

            "stone_name": stone_name,
            "element_lack": element_lack,

            "horoscope_full": result.get("destiny_map",""),
            "past": result.get("past",""),
            "present_future": result.get("present_future",""),
            "element_detail": result.get("element_diagnosis",""),

            "oracle_name": result.get("oracle_card", {}).get("name",""),
            "oracle_position": result.get("oracle_card", {}).get("position",""),

            "stones": "",
            "product_slug": "",

            "user_line_id": line_user_id
        }
        add_diagnosis(log_data)

        # 7. フロント向け返却（フル鑑定をそのまま渡す）
        full_response = {
            # まず Perplexity の結果を全部展開
            **result,

            # そこにメタ情報を上書き・追加
            "line_user_id": line_user_id,
            "diagnosis_id": diagnosis_id,
            "element_lack": element_lack,
            "stone_name": stone_name,
            # ★オラクルカード名をフロント向けにも固定キーで渡す
            "oraclecardname": result.get("oracle_card", {}).get("name", ""),
            # short_message は、将来使いたくなった時用にここで決めてもOK
            "short_message": result.get("short_message") or
            f"今のあなたに不足しているのは「{element_lack}」のエレメント。そのバランスを整える代表的な石が『{stone_name}』です。",

            # stones_for_user は、AI側が出してくれたものを優先
            "stones_for_user": result.get("stones_for_user") or stones_for_user,
        }

        elapsed_time = time.time() - start_time
        print(f"Diagnose finished in {elapsed_time:.2f}s")

        return jsonify(full_response)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500
    
def today_fortune():
    """
    今日の運勢を返すAPI。
    入力：gender, birth{date,time,place} があれば使う（なければ「不明」で補う）
    出力：{ "message": "..." } だけのシンプルなJSON
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        fortune = generate_today_fortune(data)
        # 失敗時フォールバック
        if isinstance(fortune, dict) and fortune.get("error"):
            return jsonify({"message": "今日は、肩の力を少し抜いて、自分のペースを大切に過ごす日です。"}), 200
        return jsonify({"message": fortune}), 200
    except Exception as e:
        return jsonify({
            "message": "今日は、無理をせず、心と体の声を優先してあげてください。",
            "error": str(e)
        }), 200

def build_bracelet():
    """
    第2フェーズ：石候補 + 手首サイズ + デザイン選択から、完成ブレスレットを生成
    フロントからは:
      - diagnosis_id
      - stones_for_user
      - wrist_inner_cm
      - design_style / bracelet_type
    などが送られてくる前提
    """
    start_time = time.time()
    print("--- Build Bracelet Request Started (Phase 2: Size & Design) ---")

    try:
        data = request.get_json(force=True, silent=True) or {}
        print(f"Received bracelet data: {data}")

        # 1. パラメータ取得
        diagnosis_id = data.get("diagnosis_id", str(uuid.uuid4())[:8])

        stones_for_user = data.get("stones_for_user") or [
            {"name": "水晶", "reason": "AIが石を返さなかったためデフォルト"}
        ]

        try:
            wrist_inner_cm = float(data.get("wrist_inner_cm") or 15.0)
        except ValueError as ve:
            print(f"Value Error in wrist_inner_cm: {ve}")
            wrist_inner_cm = 15.0

        # ビーズサイズはフロントで聞いていないので、今は固定 8mm とする
        bead_size_mm = 8

        # フロント側では bracelet_type を送っている想定だが、互換性のため design_style も見る
        bracelet_type = data.get("bracelet_type")
        design_style = data.get("design_style")

        bracelet_type = data.get("bracelet_type") or "element_top_only"
        # 2. ブレスレットデザイン生成
        # stones_for_user は「エレメント石」の候補（今は1個だけ）
        bracelet_design = build_bracelet_design(
            stones_for_user,
            wrist_inner_cm,
            bead_size_mm,
            bracelet_type,
            data  # birth_date など必要ならここから使えるように
        )
        stones = bracelet_design["stones"]
        design_text = bracelet_design["design_text"]



        # 3. 「あなたを導く石たち」というカスタム注文内容を生成
        order_summary = generate_stone_summary(
            stones, wrist_inner_cm, bead_size_mm, bracelet_type
        )

        elapsed_time = time.time() - start_time
        print(f"Build bracelet finished in {elapsed_time:.2f} seconds.")

        stone_counts = {s["name"]: s["count"] for s in stones}
        stones_str = format_stones(stone_counts)
        update_diagnosis(
            diagnosis_id,
            stones_str,
            ""
        )
        response_data = {
            "diagnosis_id": diagnosis_id,
            "phase": "bracelet_complete",
            "design_text": design_text,
            "stones": stones,
            "order_summary": order_summary,
            "wrist_inner_cm": wrist_inner_cm,
            "bead_size_mm": bead_size_mm,
            "design_style": bracelet_type,  # 名称は揃えるか、別フィールドにする
            "bracelet_type": bracelet_type,
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


def build_bracelet_design(
    stones_for_user: list,
    wrist_inner_cm: float,
    bead_size_mm: int,
    bracelet_type: str,
    request_data: dict
) -> dict:
    """
    stones_for_user: エレメント石の候補（今は1種類想定）
    bracelet_type:
      - "birth_top_element_side": 誕生石トップ＋エレメントサイド
      - "element_top_only": エレメントのみ
    """

    if not stones_for_user:
        return {
            "stones": [],
            "design_concept": "未指定",
            "design_text": "石の候補が取得できませんでした。"
        }

    # エレメント石（不足エレメントを補う石）
    element_stone = stones_for_user[0]

    # 誕生石（プロフィールから決める）
    birth_info = (request_data or {}).get("birth") or {}
    birth_stone = get_birthstone_from_birth(birth_info)

    bracelet_length_mm = wrist_inner_cm * 10 + 10
    total_bead_count = max(12, int(bracelet_length_mm / bead_size_mm))

    stones = []

    if bracelet_type == "birth_top_element_side":
        # 誕生石を1粒トップ、残りをエレメント石でサイドに
        surrounding_count = max(11, total_bead_count - 1)

        stones.append({
            "name": birth_stone["name"],
            "reason": birth_stone["reason"],
            "count": 1,
            "position": "accent"  # トップ
        })
        stones.append({
            "name": element_stone["name"],
            "reason": element_stone["reason"],
            "count": surrounding_count,
            "position": "side"
        })

        design_concept = f"誕生石「{birth_stone['name']}」をトップに、エレメントを整える石「{element_stone['name']}」で全体を包み込むブレスレット"

    elif bracelet_type == "element_top_only":
        # エレメント石のみで構成（実質単色）
        stones.append({
            "name": element_stone["name"],
            "reason": element_stone["reason"],
            "count": total_bead_count,
            "position": "top"
        })

        design_concept = f"不足しているエレメントを集中的に補う、{element_stone['name']}だけで仕上げたシンプルなブレスレット"

    else:
        # 万が一未知のタイプが来たときのフォールバック（単色扱い）
        stones.append({
            "name": element_stone["name"],
            "reason": element_stone["reason"],
            "count": total_bead_count,
            "position": "top"
        })
        design_concept = f"{element_stone['name']}をメインにしたブレスレット"

    design_text = generate_design_text_for_type(
        birth_stone,
        element_stone,
        stones,
        bracelet_type,
        wrist_inner_cm,
        bead_size_mm,
        design_concept
    )

    return {
        "stones": stones,
        "design_concept": design_concept,
        "design_text": design_text,
        "sales_copy": f"あなたを導く {element_stone['name']} ブレスレット"
    }


def generate_design_text_for_type(
    birth_stone: dict,
    element_stone: dict,
    stones: list,
    bracelet_type: str,
    wrist_inner_cm: float,
    bead_size_mm: int,
    design_concept: str
) -> str:
    if bracelet_type == "birth_top_element_side":
        style_desc = (
            "誕生石をブレスレットの中心に据え、その周りをエレメント石で囲むことで、"
            "『本来のあなた』と『今必要なエネルギー』の両方を同時に引き出すデザインです。"
        )
    else:  # element_top_only
        style_desc = (
            "不足しているエレメントに特化したシンプルな構成で、"
            "余計な要素をそぎ落とし、石の持つ力をダイレクトに感じやすいデザインです。"
        )

    part1 = f"""
デザインコンセプト

このブレスレットの核となる石は、**{element_stone['name']}**です。{element_stone['reason']}
{design_concept}
"""

    if bracelet_type == "birth_top_element_side":
        part2 = f"""
誕生石とエレメント石のバランス

トップには、あなたの生まれ持った流れを象徴する**{birth_stone['name']}**を一粒だけ配置しました。{birth_stone['reason']}
その周りを取り囲むように配置された**{element_stone['name']}**が、今のあなたの状態に合わせて不足しているエレメントを丁寧に補っていきます。
"""
    else:
        part2 = f"""
エレメントに特化したシンプルデザイン

ブレスレット全体を**{element_stone['name']}**のみで構成することで、テーマを一つに絞り、エネルギーの方向性をクリアにしました。
迷いや雑音を減らし、「今の自分にとって何が大事か」を見つめ直すサポートをしてくれます。
"""

    part3 = f"""
日常での使い方と効果

内径**{wrist_inner_cm}cm**、ビーズサイズ**{bead_size_mm}mm**で仕上げているため、日常使いしやすく、さりげなく身につけていられます。
{style_desc}
ふと心が揺れたときや、選択に迷ったときは、ブレスレットにそっと触れて深呼吸をしてみてください。今のあなたに必要な方向へ、すこしずつ舵を切る手助けをしてくれるはずです。
"""

    return part1 + part2 + part3


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


def get_birthstone_from_birth(birth: dict) -> dict:
    """
    生年月日から誕生石候補を返す（name, reason のdict）
    今は簡易マップ（後で細かく調整OK）
    """
    date_str = (birth or {}).get("date")
    if not date_str:
        return {"name": "水晶", "reason": "どの月とも相性がよい万能の石です。"}

    try:
        month = int(date_str.split("-")[1])
    except Exception:
        return {"name": "水晶", "reason": "どの月とも相性がよい万能の石です。"}

    BIRTHSTONE_MAP = {
        1: "ガーネット",
        2: "アメジスト",
        3: "アクアマリン",
        4: "水晶",
        5: "エメラルド",
        6: "ムーンストーン",
        7: "ルビー",
        8: "ペリドット",
        9: "サファイア",
        10: "オパール",
        11: "トパーズ",
        12: "ターコイズ",
    }
    name = BIRTHSTONE_MAP.get(month, "水晶")
    return {
        "name": name,
        "reason": f"{month}月生まれのあなたを守る誕生石です。"
    }
