"""Google Sheets連携モジュール

スプレッドシートへの診断結果・注文・プロフィールの読み書き機能を提供する。
gspread ライブラリを使用してGoogle Sheets APIにアクセスする。

改善点:
- クライアントとワークシートのキャッシュ（レイテンシ改善）
- 書き込みリトライロジック（信頼性向上）
- ヘッダー行の自動作成（初回セットアップ対応）
"""

import os
import json
import time
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

# 各シートの期待するヘッダー行
EXPECTED_HEADERS = {
    LOG_SHEET_NAME: [
        "diagnosis_id", "created_at", "stone_name", "element_lack",
        "horoscope_full", "past", "present_future", "element_detail",
        "oracle_name", "oracle_position", "stones", "product_slug",
        "user_line_id", "purchased",
    ],
    ORDER_SHEET_NAME: [
        "order_id", "created_at", "status",
        "diagnosis_id", "line_user_id",
        "customer_name", "customer_email", "customer_phone",
        "product_name", "product_id", "sku", "quantity",
        "total", "payment_method",
    ],
    PROFILE_SHEET_NAME: [
        "user_id", "gender", "birth_date", "birth_time",
        "birth_place", "wrist_inner_cm", "bead_size_mm", "bracelet_type",
    ],
}

# ===== キャッシュ =====

# キャッシュの有効期間（秒）: Vercelのコールドスタート対策
# サーバーレス環境ではプロセスが再利用される間はキャッシュが効く
CACHE_TTL = 300  # 5分

_client_cache: dict = {"client": None, "expires": 0}
_worksheet_cache: dict = {}  # {sheet_name: {"ws": worksheet, "expires": timestamp}}


def _get_client() -> gspread.Client:
    """認証済みgspreadクライアントを返す（キャッシュ付き）"""
    now = time.time()

    if _client_cache["client"] and now < _client_cache["expires"]:
        return _client_cache["client"]

    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not creds_json:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON 環境変数が設定されていません")

    info = json.loads(creds_json)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    client = gspread.authorize(creds)

    _client_cache["client"] = client
    _client_cache["expires"] = now + CACHE_TTL

    logger.info("Google Sheets クライアントを新規作成しました")
    return client


def _get_sheet_id() -> str:
    """スプレッドシートIDを取得する"""
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "")
    if not sheet_id:
        raise RuntimeError("GOOGLE_SHEET_ID 環境変数が設定されていません")
    return sheet_id


def _get_worksheet(sheet_name: str) -> gspread.Worksheet:
    """指定名のワークシートを返す（キャッシュ付き）"""
    now = time.time()
    cached = _worksheet_cache.get(sheet_name)

    if cached and now < cached["expires"]:
        return cached["ws"]

    client = _get_client()
    sh = client.open_by_key(_get_sheet_id())

    try:
        ws = sh.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        # ワークシートが存在しない場合は新規作成
        logger.info(f"ワークシート '{sheet_name}' が見つかりません。新規作成します。")
        ws = sh.add_worksheet(title=sheet_name, rows=1000, cols=20)

    # ヘッダー行の確認・作成
    _ensure_headers(ws, sheet_name)

    _worksheet_cache[sheet_name] = {"ws": ws, "expires": now + CACHE_TTL}
    return ws


def _ensure_headers(ws: gspread.Worksheet, sheet_name: str):
    """ヘッダー行を確認し、期待する列と一致しない場合は1行目を更新する"""
    expected = EXPECTED_HEADERS.get(sheet_name)
    if not expected:
        return

    try:
        first_row = ws.row_values(1)
        if first_row == expected:
            return  # 一致しているので何もしない

        # 空、または期待と異なる場合は1行目を上書き
        ws.update('A1', [expected], value_input_option='USER_ENTERED')
        logger.info("ヘッダー行を更新しました: %s (%d列)", sheet_name, len(expected))
    except Exception as e:
        logger.warning("ヘッダー行確認エラー (%s): %s", sheet_name, e)


def _invalidate_cache(sheet_name: str = None):
    """キャッシュを無効化する"""
    if sheet_name:
        _worksheet_cache.pop(sheet_name, None)
    else:
        _worksheet_cache.clear()
        _client_cache["client"] = None
        _client_cache["expires"] = 0


def _get_log_sheet() -> gspread.Worksheet:
    return _get_worksheet(LOG_SHEET_NAME)


def _get_order_sheet() -> gspread.Worksheet:
    return _get_worksheet(ORDER_SHEET_NAME)


def _get_profile_sheet() -> gspread.Worksheet:
    return _get_worksheet(PROFILE_SHEET_NAME)


# ===== リトライ付き書き込み =====

def _append_row_with_retry(sheet: gspread.Worksheet, row: list, max_retries: int = 3):
    """リトライ付きで行を追加する

    Google Sheets APIのレート制限やネットワークエラーに対応。
    value_input_option='USER_ENTERED' を使用して正しく書き込む。
    """
    for attempt in range(max_retries):
        try:
            sheet.append_row(
                row,
                value_input_option='USER_ENTERED',
            )
            return
        except gspread.exceptions.APIError as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 1.5
                logger.warning(
                    f"Sheets API書き込みエラー (試行 {attempt + 1}/{max_retries}): {e}. "
                    f"{wait_time}秒後にリトライ..."
                )
                time.sleep(wait_time)
                # キャッシュを無効化して再取得を強制
                _invalidate_cache()
            else:
                logger.error(f"Sheets API書き込み最終エラー: {e}")
                raise
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"書き込みエラー (試行 {attempt + 1}/{max_retries}): {e}")
                time.sleep(1)
                _invalidate_cache()
            else:
                raise


def _update_cell_with_retry(
    sheet: gspread.Worksheet, row: int, col: int, value, max_retries: int = 3
):
    """リトライ付きでセルを更新する"""
    for attempt in range(max_retries):
        try:
            sheet.update_cell(row, col, value)
            return
        except gspread.exceptions.APIError as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 1.5
                logger.warning(
                    f"セル更新エラー (試行 {attempt + 1}/{max_retries}): {e}. "
                    f"{wait_time}秒後にリトライ..."
                )
                time.sleep(wait_time)
            else:
                logger.error(f"セル更新最終エラー: {e}")
                raise
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                raise


# ===== 注文操作 =====

def add_order(data: dict):
    """注文データをスプレッドシートに追加する"""
    sheet = _get_order_sheet()

    row = [
        data.get("order_id", ""),
        data.get("created_at", ""),
        data.get("status", ""),
        data.get("diagnosis_id", ""),
        data.get("line_user_id", ""),
        data.get("customer_name", ""),
        data.get("customer_email", ""),
        data.get("customer_phone", ""),
        data.get("product_name", ""),
        data.get("product_id", ""),
        data.get("sku", ""),
        data.get("quantity", ""),
        data.get("total", ""),
        data.get("payment_method", ""),
    ]

    _append_row_with_retry(sheet, row)
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

    _append_row_with_retry(sheet, row)
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
        _update_cell_with_retry(sheet, row, stones_col, stones)
    except ValueError:
        logger.warning("stonesカラムが見つかりません")

    if product_slug:
        try:
            slug_col = headers.index("product_slug") + 1
            _update_cell_with_retry(sheet, row, slug_col, product_slug)
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
        _update_cell_with_retry(sheet, row, col_index, True)
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
            _update_cell_with_retry(ws, row, col_index[col_name], value)

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
