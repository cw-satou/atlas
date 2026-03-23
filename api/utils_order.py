"""注文関連ユーティリティ

ブレスレット注文のサマリー生成や管理者通知テキストの作成を行う。
"""

from typing import Dict, Any


def build_order_summary(
    diagnosis_result: Dict[str, Any],
    wrist_inner_cm: float,
    bead_size_mm: int,
) -> Dict[str, str]:
    """診断結果からオーダーサマリーを生成する

    Args:
        diagnosis_result: 診断結果（stones配列を含む辞書）
        wrist_inner_cm: 手首の内径（cm）
        bead_size_mm: ビーズサイズ（mm）

    Returns:
        order_line, internal_note, sales_copy を含む辞書
    """
    stones = diagnosis_result.get("stones", [])

    # 「アメジスト×15、ブルータイガーアイ×3」形式のテキスト生成
    stone_parts = []
    for s in stones:
        name = s.get("name", "不明な石")
        count = s.get("count", 0)
        stone_parts.append(f"{name}×{count}")
    stones_text = "、".join(stone_parts) if stone_parts else "未指定"

    order_line = f"内径{wrist_inner_cm}cm、{stones_text}"

    reading = diagnosis_result.get("reading", "")
    design_concept = diagnosis_result.get("design_concept", "無題")
    design_text = diagnosis_result.get("design_text", "")

    internal_note = (
        f"[占い要約]\n{reading}\n\n"
        f"[デザインコンセプト]\n{design_concept}\n"
        f"{design_text}\n\n"
        f"[仕様メモ]\n"
        f"- 手首内径: {wrist_inner_cm}cm\n"
        f"- ビーズサイズ: {bead_size_mm}mm\n"
        f"- 石構成: {stones_text}\n"
    )

    sales_copy = diagnosis_result.get("sales_copy", "")
    if not sales_copy:
        sales_copy = (
            f"【{design_concept}】\n\n"
            f"{reading}\n\n"
            f"手首{wrist_inner_cm}cm前後の方向けに、{stones_text}でお作りするブレスレットです。"
        )

    return {
        "order_line": order_line,
        "internal_note": internal_note,
        "sales_copy": sales_copy,
    }


def build_admin_notification(line_user_id: str, order_summary: Dict[str, str]) -> str:
    """管理者向けの注文通知テキストを生成する"""
    return (
        "【新規オーダーが入りました】\n"
        f"- LINEユーザーID: {line_user_id}\n"
        f"- 注文内容: {order_summary['order_line']}\n\n"
        f"▼内部メモ\n{order_summary['internal_note']}"
    )
