import os
import json
import gspread
from google.oauth2.service_account import Credentials
from oauth2client.service_account import ServiceAccountCredentials

# 認証まわりは既存のをそのまま使ってOK
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
creds = ServiceAccountCredentials.from_json_keyfile_name(
    "service_account.json", scope
)
gc = gspread.authorize(creds)

PROFILE_SHEET_KEY = "スプレッドシートID_profiles"
LOG_SHEET_KEY = "スプレッドシートID_logs"
# ==========================
# Client生成
# ==========================


def get_client():
    service_account_info = json.loads(
        os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    )
    creds = Credentials.from_service_account_info(
        service_account_info,
        scopes=SCOPES
    )
    return gspread.authorize(creds)


def get_sheet():
    client = get_client()
    sheet = client.open_by_key(
        os.environ["GOOGLE_SHEET_ID"]
    ).sheet1
    return sheet


# ==========================
# 追加保存
# ==========================
def add_diagnosis(data: dict):
    sheet = get_sheet()

    row = [
        data.get("diagnosis_id", ""),
        data.get("created_at", ""),
        data.get("stone_name", ""),
        data.get("element_lack", ""),
        data.get("horoscope_full", ""),
        data.get("past", ""),
        data.get("present", ""),
        data.get("future", ""),
        data.get("element_detail", ""),
        data.get("oracle_name", ""),
        data.get("oracle_position", ""),
        data.get("product_slug", ""),
        "",          # user_line_id
        False        # purchased
    ]

    sheet.append_row(row, value_input_option="USER_ENTERED")


# ==========================
# 1件取得（高速版）
# ==========================
def get_diagnosis(diagnosis_id: str):
    sheet = get_sheet()

    # 全行取得せず、1列目のみ取得
    id_column = sheet.col_values(1)

    if diagnosis_id not in id_column:
        return None

    row_index = id_column.index(diagnosis_id) + 1
    row_data = sheet.row_values(row_index)

    headers = sheet.row_values(1)

    return dict(zip(headers, row_data))


def get_profile_sheet():
    client = get_client()
    # スプレッドシート内の「プロフィール」シートを前提
    return client.open_by_key(
        os.environ["GOOGLE_SHEET_ID"]
    ).worksheet("プロフィール")


def upsert_profile(profile: dict):
    """
    profile 例:
    {
      "user_id": "xxxx",
      "gender": "女性",
      "birth": {
          "date": "1990-01-01",
          "time": "12:00",
          "place": "札幌市"
      },
      "wrist_inner_cm": 15.0,
      "bead_size_mm": 8,
      "bracelet_type": "birth_top_element_side",
    }
    """
    sh = gc.open_by_key(PROFILE_SHEET_KEY)
    ws = sh.worksheet("profiles")  # シート名は profiles 想定

    # 1行目ヘッダー → 列名と列番号の対応を作る
    header = ws.row_values(1)
    col_index = {name: i + 1 for i, name in enumerate(header)}  # 1始まり

    user_id = profile["user_id"]

    # birth をフラットに
    birth = profile.get("birth", {}) or {}
    birth_date = birth.get("date", "")
    birth_time = birth.get("time", "")
    birth_place = birth.get("place", "")

    # 1. user_id で既存行を探す（なければ新規）
    try:
        cell = ws.find(user_id)  # 見つからなければ例外
        row = cell.row
    except Exception:
        row = ws.row_count + 1  # 次の空行に新規作成

    # 2. 必ず書き込み（存在すれば更新、なければ新規）
    def set_cell(col_name, value):
        if col_name not in col_index:
            return
        col = col_index[col_name]
        ws.update_cell(row, col, value)

    set_cell("user_id", user_id)
    set_cell("gender", profile.get("gender", ""))
    set_cell("birth_date", birth_date)
    set_cell("birth_time", birth_time)
    set_cell("birth_place", birth_place)
    set_cell("wrist_inner_cm", profile.get("wrist_inner_cm", ""))
    set_cell("bead_size_mm", profile.get("bead_size_mm", ""))
    set_cell("bracelet_type", profile.get("bracelet_type", ""))

    wb.save(PROFILE_FILE)


def get_profile(user_id: str):
    sheet = get_profile_sheet()

    id_column = sheet.col_values(1)  # A列
    if user_id not in id_column:
        return None

    row_index = id_column.index(user_id) + 1
    row_data = sheet.row_values(row_index)

    # ヘッダー行（1行目）を辞書キーとして使う
    headers = sheet.row_values(1)
    data = dict(zip(headers, row_data))

    # API で返しやすい形に整形
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
