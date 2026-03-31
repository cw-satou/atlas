"""WooCommerce Webhook処理モジュール

WooCommerceから注文通知を受け取り、以下を実行する:
1. Webhook署名を検証（WOO_WEBHOOK_SECRET が設定されている場合）
2. 注文情報をGoogleスプレッドシートに記録
3. diagnosis_idが紐づく場合：購入済みフラグ更新 + LINE通知
4. 管理者へメール通知

環境変数:
    WOO_WEBHOOK_SECRET: WooCommerce Webhookシークレット（署名検証用）
    LINE_CHANNEL_ACCESS_TOKEN: LINE通知用トークン
    SMTP_HOST / SMTP_USER 等: メール通知用
"""

import os
import hmac
import hashlib
import base64
import logging
from flask import request, jsonify
from api.utils_sheet import add_order, get_diagnosis, mark_purchased
from api.utils_line import push_line
from api.utils_mail import send_order_mail

logger = logging.getLogger(__name__)


def _verify_signature(payload: bytes) -> bool:
    """WooCommerce Webhookの署名を検証する。
    WOO_WEBHOOK_SECRET が未設定の場合は検証をスキップ（警告のみ）。
    """
    secret = os.environ.get("WOO_WEBHOOK_SECRET", "")
    if not secret:
        logger.warning("WOO_WEBHOOK_SECRET が未設定です。署名検証をスキップします。")
        return True

    sig_header = request.headers.get("X-WC-Webhook-Signature", "")
    if not sig_header:
        logger.warning("X-WC-Webhook-Signature ヘッダーがありません")
        return False

    expected = base64.b64encode(
        hmac.new(secret.encode(), payload, hashlib.sha256).digest()
    ).decode()
    return hmac.compare_digest(expected, sig_header)


def _extract_diagnosis_id(order: dict) -> str | None:
    """注文のメタデータから diagnosis_id を抽出する。
    WooCommerce側で diagnosis_id を order meta に保存している場合に機能する。
    """
    # 注文レベルのメタデータを確認
    for meta in order.get("meta_data", []):
        if meta.get("key") == "diagnosis_id":
            return meta.get("value")
    # 商品アイテムのメタデータも確認
    for item in order.get("line_items", []):
        for meta in item.get("meta_data", []):
            if meta.get("key") == "diagnosis_id":
                return meta.get("value")
    return None


def _extract_order_data(order: dict, diagnosis_id: str | None, line_user_id: str | None) -> dict:
    """WooCommerce注文JSONから保存用データを構築する"""
    billing = order.get("billing", {})
    customer_name = f"{billing.get('last_name', '')} {billing.get('first_name', '')}".strip()

    # 最初の商品アイテムを代表として記録（複数商品の場合はカンマ結合）
    items = order.get("line_items", [])
    product_names = ", ".join(i.get("name", "") for i in items)
    product_ids   = ", ".join(str(i.get("product_id", "")) for i in items)
    skus          = ", ".join(i.get("sku", "") for i in items)
    quantities    = ", ".join(str(i.get("quantity", "")) for i in items)

    return {
        "order_id":       str(order.get("id", "")),
        "created_at":     order.get("date_created", ""),
        "status":         order.get("status", ""),
        "diagnosis_id":   diagnosis_id or "",
        "line_user_id":   line_user_id or "",
        "customer_name":  customer_name,
        "customer_email": billing.get("email", ""),
        "customer_phone": billing.get("phone", ""),
        "product_name":   product_names,
        "product_id":     product_ids,
        "sku":            skus,
        "quantity":       quantities,
        "total":          order.get("total", ""),
        "payment_method": order.get("payment_method_title", ""),
    }


def woo_webhook():
    """WooCommerce Webhook エンドポイント"""
    try:
        payload = request.get_data()

        # 署名検証
        if not _verify_signature(payload):
            logger.warning("Webhook: 署名検証失敗")
            return jsonify({"status": "invalid signature"}), 401

        order = request.get_json(force=True, silent=True)
        if not order:
            logger.warning("Webhook: リクエストボディが空です")
            return jsonify({"status": "empty request"}), 400

        order_id = order.get("id")
        if not order_id:
            logger.warning("Webhook: order_id が見つかりません")
            return jsonify({"status": "missing order_id"}), 400

        logger.info("Webhook受信: order_id=%s status=%s", order_id, order.get("status"))

        # diagnosis_id を取得し、紐づく LINE ユーザーIDも取得
        diagnosis_id = _extract_diagnosis_id(order)
        line_user_id = None
        diagnosis = None

        if diagnosis_id:
            diagnosis = get_diagnosis(diagnosis_id)
            if diagnosis:
                line_user_id = diagnosis.get("line_user_id") or diagnosis.get("user_line_id")
            else:
                logger.warning("Webhook: diagnosis_id=%s が見つかりません", diagnosis_id)

        # スプレッドシートに記録
        order_data = _extract_order_data(order, diagnosis_id, line_user_id)
        try:
            add_order(order_data)
            logger.info("Webhook: 注文保存完了 order_id=%s", order_id)
        except Exception as e:
            logger.error("Webhook: スプレッドシート書き込みエラー: %s", e)

        # 購入済みフラグを更新
        if diagnosis_id and diagnosis:
            try:
                mark_purchased(diagnosis_id)
            except Exception as e:
                logger.warning("Webhook: 購入済みフラグ更新失敗: %s", e)

        # 管理者へメール通知
        try:
            send_order_mail(order_data, diagnosis_id or f"order-{order_id}")
        except Exception as e:
            logger.warning("Webhook: メール通知失敗: %s", e)

        # LINEユーザーへ通知（LINE登録ユーザーのみ）
        if line_user_id:
            product_text = order_data.get("product_name", "ご注文の商品")
            message = (
                f"ご注文ありがとうございます\n\n"
                f"商品：{product_text}\n"
                f"合計：¥{order_data.get('total', '')}\n\n"
                "制作を開始します。完成次第ご連絡します。"
            )
            if not push_line(line_user_id, message):
                logger.warning("Webhook: LINE通知失敗 order_id=%s", order_id)
        else:
            logger.info("Webhook: LINE未登録ユーザーのため通知スキップ order_id=%s", order_id)

        return jsonify({"status": "ok", "order_id": order_id})

    except Exception:
        logger.exception("Webhook処理中にエラーが発生しました")
        return jsonify({"status": "error"}), 500
