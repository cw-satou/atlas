"""Google Sheets連携モジュール

スプレッドシートへの診断結果・注文・プロフィールの読み書き機能を提供する。
gspread ライブラリを使用してGoogle Sheets APIにアクセスする。
"""

import os
import json
import logging
import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

# シート名定義
PROFILE_SHEET_NAME = "profiles"
LOG_SHEET_NAME = "diagnosis_logs"
ORDER_SHEET_NAME = "orders"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


# ===== クライアント生成 =====

def _get_client() -> gspread.Client:
    """認証済みgspreadクライアントを返す"""
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not creds_json:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON 環境変数が設定されていません")

    info = json.loads(creds_json)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_sheet_id() -> str:
    """スプレッドシートIDを取得する"""
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "")
    if not sheet_id:
        raise RuntimeError("GOOGLE_SHEET_ID 環境変数が設定されていません")
    return sheet_id


def _get_worksheet(sheet_name: str) -> gspread.Worksheet:
    """指定名のワークシートを返す"""
    client = _get_client()
    sh = client.open_by_key(_get_sheet_id())
    return sh.worksheet(sheet_name)


def _get_log_sheet() -> gspread.Worksheet:
    return _get_worksheet(LOG_SHEET_NAME)


def _get_order_sheet() -> gspread.Worksheet:
    return _get_worksheet(ORDER_SHEET_NAME)


def _get_profile_sheet() -> gspread.Worksheet:
    return _get_worksheet(PROFILE_SHEET_NAME)


# ===== 注文操作 =====

def add_order(data: dict):
    """注文データをスプレッドシートに追加する"""
    sheet = _get_order_sheet()

    row = [
        data.get("order_id", ""),
        data.get("diagnosis_id", ""),
        data.get("user_line_id", ""),
        data.get("product_slug", ""),
        data.get("stones", ""),
        data.get("wrist_inner_cm", ""),
        data.get("bead_size_mm", ""),
        data.get("bracelet_type", ""),
        data.get("order_status", "pending"),
        data.get("created_at", ""),
    ]

    sheet.append_row(row, table_range="A1")
    logger.info(f"注文追加完了: order_id={data.get('order_id')}")


# ===== 診断ログ操作 =====

def add_diagnosis(data: dict):
    """診断結果をスプレッドシートに追加する"""
    sheet = _get_log_sheet()

    row = [
        data.get("diagnosis_id", ""),
        data.get("created_at", ""),
        data.get("stone_name", ""),
        data.get("element_lack", ""),
        data.get("horoscope_full", ""),
        data.get("past", ""),
        data.get("present_future", ""),
        data.get("element_detail", ""),
        data.get("oracle_name", ""),
        data.get("oracle_position", ""),
        data.get("stones", ""),
        data.get("product_slug", ""),
        data.get("user_line_id", ""),
        False,  # purchased フラグ
    ]

    sheet.append_row(row, table_range="A1")
    logger.info(f"診断ログ追加完了: diagnosis_id={data.get('diagnosis_id')}")


def update_diagnosis(diagnosis_id: str, stones: str, product_slug: str):
    """診断レコードの石情報と商品スラッグを更新する"""
    sheet = _get_log_sheet()
    id_column = sheet.col_values(1)

    if diagnosis_id not in id_column:
        logger.warning(f"更新対象の診断が見つかりません: {diagnosis_id}")
        return

    row = id_column.index(diagnosis_id) + 1
    headers = sheet.row_values(1)

    try:
        stones_col = headers.index("stones") + 1
        sheet.update_cell(row, stones_col, stones)
    except ValueError:
        logger.warning("stonesカラムが見つかりません")

    try:
        slug_col = headers.index("product_slug") + 1
        sheet.update_cell(row, slug_col, product_slug)
    except ValueError:
        logger.warning("product_slugカラムが見つかりません")


def mark_purchased(diagnosis_id: str):
    """診断レコードの購入済みフラグを更新する"""
    sheet = _get_log_sheet()
    id_column = sheet.col_values(1)

    if diagnosis_id not in id_column:
        logger.warning(f"購入マーク対象の診断が見つかりません: {diagnosis_id}")
        return

    row = id_column.index(diagnosis_id) + 1
    headers = sheet.row_values(1)

    try:
        col_index = headers.index("purchased") + 1
        sheet.update_cell(row, col_index, True)
    except ValueError:
        logger.warning("purchasedカラムが見つかりません")


def get_diagnosis(diagnosis_id: str) -> dict | None:
    """diagnosis_idで診断レコードを1件取得する"""
    if not diagnosis_id:
        return None

    sheet = _get_log_sheet()
    id_column = sheet.col_values(1)

    if diagnosis_id not in id_column:
        return None

    row_index = id_column.index(diagnosis_id) + 1
    row_data = sheet.row_values(row_index)
    headers = sheet.row_values(1)

    return dict(zip(headers, row_data))


def format_stones(stone_counts: dict) -> str:
    """石のカウント辞書をフォーマット文字列に変換する

    例: {"アメジスト": 2, "ローズ": 14} → "アメジスト×2,ローズ×14"
    """
    parts = [f"{name}×{count}" for name, count in stone_counts.items()]
    return ",".join(parts)


# ===== プロフィール操作 =====

def upsert_profile(profile: dict):
    """ユーザープロフィールを追加または更新する

    Args:
        profile: user_id, gender, birth{date,time,place}, wrist_inner_cm 等を含む辞書
    """
    ws = _get_profile_sheet()
    header = ws.row_values(1)
    col_index = {name: i + 1 for i, name in enumerate(header)}

    user_id = profile.get("user_id")
    if not user_id:
        logger.warning("upsert_profile: user_idが未指定です")
        return

    birth = profile.get("birth", {}) or {}

    # 既存行を検索（なければ新規行）
    try:
        cell = ws.find(user_id)
        row = cell.row
    except gspread.exceptions.CellNotFound:
        row = len(ws.get_all_values()) + 1

    def set_cell(col_name: str, value):
        if col_name in col_index:
            ws.update_cell(row, col_index[col_name], value)

    set_cell("user_id", user_id)
    set_cell("gender", profile.get("gender", ""))
    set_cell("birth_date", birth.get("date", ""))
    set_cell("birth_time", birth.get("time", ""))
    set_cell("birth_place", birth.get("place", ""))
    set_cell("wrist_inner_cm", profile.get("wrist_inner_cm", ""))
    set_cell("bead_size_mm", profile.get("bead_size_mm", ""))
    set_cell("bracelet_type", profile.get("bracelet_type", ""))


def get_profile(user_id: str) -> dict | None:
    """ユーザーIDでプロフィールを取得する"""
    if not user_id:
        return None

    sheet = _get_profile_sheet()
    id_column = sheet.col_values(1)

    if user_id not in id_column:
        return None

    row_index = id_column.index(user_id) + 1
    row_data = sheet.row_values(row_index)
    headers = sheet.row_values(1)

    data = dict(zip(headers, row_data))

    return {
        "user_id": data.get("user_id"),
        "gender": data.get("gender"),
        "birth": {
            "date": data.get("birth_date"),
            "time": data.get("birth_time"),
            "place": data.get("birth_place"),
        },
        "wrist_inner_cm": float(data["wrist_inner_cm"]) if data.get("wrist_inner_cm") else None,
        "bead_size_mm": int(data["bead_size_mm"]) if data.get("bead_size_mm") else None,
        "bracelet_type": data.get("bracelet_type"),
    }
