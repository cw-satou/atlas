"""WooCommerce Webhook処理モジュール

WooCommerceから注文通知を受け取り、以下を実行する:
1. 注文情報をGoogleスプレッドシートに記録
2. 診断結果に紐づくLINEユーザーに注文確認メッセージを送信
"""

import logging
from flask import request, jsonify
from api.utils_sheet import add_order, get_diagnosis, mark_purchased
from api.utils_line import push_line

logger = logging.getLogger(__name__)


def _extract_diagnosis_id(order: dict) -> str | None:
    """注文のline_itemsからdiagnosis_idメタデータを抽出する"""
    for item in order.get("line_items", []):
        for meta in item.get("meta_data", []):
            if meta.get("key") == "diagnosis_id":
                return meta.get("value")
    return None


def woo_webhook():
    """WooCommerce Webhook エンドポイント"""
    try:
        order = request.get_json(force=True, silent=True)
        if not order:
            logger.warning("Webhook: リクエストボディが空です")
            return jsonify({"status": "empty request"}), 400

        order_id = order.get("id")
        if not order_id:
            logger.warning("Webhook: order_id が見つかりません")
            return jsonify({"status": "missing order_id"}), 400

        # 注文からdiagnosis_idを抽出
        diagnosis_id = _extract_diagnosis_id(order)

        # 注文データをスプレッドシートに記録
        data = {
            "order_id": order_id,
            "diagnosis_id": diagnosis_id or "",
            "created_at": order.get("date_created", ""),
        }
        add_order(data)

        # diagnosis_idがない場合はここで終了
        if not diagnosis_id:
            logger.info(f"Webhook: 注文 {order_id} にdiagnosis_idが含まれていません")
            return jsonify({"status": "ok", "note": "no diagnosis_id"})

        # 診断結果を取得
        diagnosis = get_diagnosis(diagnosis_id)
        if not diagnosis:
            logger.warning(f"Webhook: diagnosis_id={diagnosis_id} が見つかりません")
            return jsonify({"status": "diagnosis not found"})

        # 購入済みフラグを更新
        try:
            mark_purchased(diagnosis_id)
        except Exception as e:
            logger.warning(f"Webhook: 購入済みフラグ更新失敗: {e}")

        # LINEユーザーにメッセージ送信
        user_id = diagnosis.get("user_line_id")
        if not user_id:
            logger.info(f"Webhook: 診断 {diagnosis_id} にLINEユーザーIDがありません")
            return jsonify({"status": "ok", "note": "no LINE user_id"})

        stones = diagnosis.get("stones", "未定")
        message = (
            "ご注文ありがとうございます\n\n"
            f"使用する石: {stones}\n\n"
            "制作を開始します。"
        )
        push_line(user_id, message)

        logger.info(f"Webhook: 注文 {order_id} の処理完了（LINE通知送信済み）")
        return jsonify({"status": "ok"})

    except Exception as e:
        logger.exception("Webhook処理中にエラーが発生しました")
        return jsonify({"status": "error", "message": str(e)}), 500
