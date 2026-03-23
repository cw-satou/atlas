"""LINE Messaging API ユーティリティ

LINEプッシュメッセージの送信機能を提供する。
"""

import os
import logging
import requests

logger = logging.getLogger(__name__)

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"


def push_line(user_id: str, message: str) -> bool:
    """LINEユーザーにプッシュメッセージを送信する

    Args:
        user_id: LINEユーザーID
        message: 送信するテキストメッセージ

    Returns:
        送信成功時はTrue、失敗時はFalse
    """
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")

    if not token:
        logger.warning("LINE_CHANNEL_ACCESS_TOKEN が設定されていません")
        return False

    if not user_id:
        logger.warning("LINEユーザーIDが空です")
        return False

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    body = {
        "to": user_id,
        "messages": [
            {
                "type": "text",
                "text": message,
            }
        ],
    }

    try:
        resp = requests.post(LINE_PUSH_URL, json=body, headers=headers, timeout=10)
        if resp.status_code != 200:
            logger.error(
                f"LINE Push API エラー: status={resp.status_code}, body={resp.text}"
            )
            return False
        logger.info(f"LINEメッセージ送信成功: user_id={user_id[:8]}...")
        return True
    except requests.RequestException as e:
        logger.error(f"LINE Push APIリクエスト失敗: {e}")
        return False
