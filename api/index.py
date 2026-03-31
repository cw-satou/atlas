from flask import Flask, request, jsonify
import os
import logging
from dotenv import load_dotenv

load_dotenv()  # ローカル開発時に .env を読み込む（本番では無視される）

from api.diagnose import diagnose, build_bracelet
from api.utils_sheet import get_diagnosis, upsert_profile, get_profile
from api.utils_perplexity import generate_today_fortune, calculate_chart
from api.utils_geocode import geocode
from api.woo_webhook import woo_webhook
from api.utils_woo import fetch_woo_products
from api.utils_rate_limit import rate_limited
from api.utils_sheet import get_config, set_config

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='public', static_url_path='')


# ===== 診断関連ルート =====

@app.route('/api/diagnose', methods=['POST'])
@rate_limited
def route_diagnose():
    """占い診断（第1フェーズ：エレメント＆メインストーン選定）"""
    return diagnose()


@app.route('/api/build-bracelet', methods=['POST'])
@rate_limited
def route_build_bracelet():
    """ブレスレット生成（第2フェーズ：サイズ＆デザイン決定）"""
    return build_bracelet()


@app.route('/api/fortune-detail', methods=['POST'])
def fortune_detail():
    """保存済み診断結果の詳細取得"""
    data = request.get_json(force=True, silent=True) or {}
    diagnosis_id = data.get("diagnosis_id")

    if not diagnosis_id:
        return jsonify({"error": "診断IDが必要です"}), 400

    saved = get_diagnosis(diagnosis_id)
    if not saved:
        return jsonify({"error": "診断結果が見つかりません"}), 404

    # 保存済みの推薦商品スラッグからWooCommerce情報を取得
    product_slug = saved.get("product_slug", "")
    woo_details: dict = {}

    return jsonify({
        "diagnosis_id":    saved.get("diagnosis_id"),
        "stone_name":      saved.get("stone_name"),
        "past":            saved.get("past"),
        "present_future":  saved.get("present_future"),
        "element_detail":  saved.get("element_detail"),
        "oracle_name":     saved.get("oracle_name"),
        "oracle_position": saved.get("oracle_position"),
        "product_slug":    product_slug,
    })


@app.route("/api/today-fortune", methods=["POST"])
@rate_limited
def today_fortune():
    """今日の運勢API（生年月日・出生時間・出生地ベース）"""
    try:
        data = request.get_json(force=True, silent=True) or {}

        # ホロスコープ計算（出生情報があれば実際のチャートを計算）
        chart_data = None
        birth = data.get("birth", {})
        if birth.get("date") and birth.get("time"):
            try:
                lat, lon = geocode(birth.get("place", ""))
                chart_data = calculate_chart(
                    birth["date"], birth["time"], lat, lon
                )
            except Exception as e:
                logger.warning(f"今日の運勢: ホロスコープ計算エラー: {e}")

        message = generate_today_fortune(data, chart_data=chart_data)
        return jsonify({"message": message}), 200
    except Exception as e:
        logger.exception("今日の運勢API エラー")
        return jsonify({
            "message": "今日は、無理をせず、自分のペースを大切に過ごすと良さそうな日です。",
        }), 200


# ===== WooCommerce Webhook =====

@app.route('/api/woo-webhook', methods=['POST'])
def route_woo_webhook():
    """WooCommerce注文受信Webhook"""
    return woo_webhook()


# ===== プロフィール管理 =====

@app.route('/api/profile', methods=['GET', 'POST'])
def route_profile():
    """ユーザープロフィールの取得・更新"""
    if request.method == 'POST':
        body = request.get_json(force=True, silent=True) or {}
        user_id = body.get("user_id")
        if not user_id:
            return jsonify({"error": "ユーザーIDが必要です"}), 400
        try:
            upsert_profile(body)
            profile = get_profile(user_id)
            return jsonify(profile or {})
        except Exception as e:
            logger.exception("プロフィール保存エラー")
            return jsonify({"error": "プロフィールの保存に失敗しました"}), 500

    # GET
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "ユーザーIDが必要です"}), 400
    try:
        profile = get_profile(user_id)
        if not profile:
            return jsonify({"error": "プロフィールが見つかりません"}), 404
        return jsonify(profile)
    except Exception as e:
        logger.exception("プロフィール取得エラー")
        return jsonify({"error": "プロフィールの読み込みに失敗しました"}), 500


# ===== ヘルスチェック & フロントエンド =====

@app.route('/api/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "ok", "service": "星の羅針盤 API"})


@app.route('/api/health/gemini/models', methods=['GET'])
def health_gemini_models():
    """利用可能なGeminiモデル一覧を取得（画像生成対応モデルを抽出）"""
    import os, requests as req
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return jsonify({"status": "error", "message": "GEMINI_API_KEY が未設定"}), 500
    try:
        resp = req.get(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
            timeout=10,
        )
        if resp.status_code != 200:
            return jsonify({"status": "error", "http_status": resp.status_code}), 500
        models = resp.json().get("models", [])
        # generateContent対応 かつ flash/image/imagen を含むモデルを抽出
        image_related = [
            {"name": m["name"], "methods": m.get("supportedGenerationMethods", [])}
            for m in models
            if any(kw in m["name"].lower() for kw in ["flash", "image", "imagen"])
            and "generateContent" in m.get("supportedGenerationMethods", [])
        ]
        return jsonify({"status": "ok", "image_related_models": image_related})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/health/gemini', methods=['GET'])
def health_gemini():
    """Gemini画像生成APIの疎通確認"""
    import os, requests as req
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return jsonify({"status": "error", "message": "GEMINI_API_KEY が未設定"}), 500

    from api.utils_image import GEMINI_MODEL, GEMINI_ENDPOINT
    try:
        resp = req.post(
            GEMINI_ENDPOINT,
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": "A simple blue circle on white background"}]}],
                "generationConfig": {"responseModalities": ["IMAGE"]},
            },
            timeout=120,
        )
        if resp.status_code != 200:
            return jsonify({
                "status": "error",
                "model": GEMINI_MODEL,
                "http_status": resp.status_code,
                "response": resp.text[:500],
            }), 500

        data = resp.json()
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        has_image = any(p.get("inlineData") for p in parts)
        return jsonify({
            "status": "ok" if has_image else "no_image",
            "model": GEMINI_MODEL,
            "parts": [list(p.keys()) for p in parts],
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/health/gcs', methods=['GET'])
def health_gcs():
    """Google Cloud Storage画像保存の診断エンドポイント"""
    import os
    result = {}

    bucket_name = os.environ.get("GCS_BUCKET_NAME", "")
    result["GCS_BUCKET_NAME"] = bucket_name[:12] + "..." if bucket_name else "❌ 未設定"

    if not bucket_name:
        return jsonify({"status": "error", "detail": result,
                        "message": "GCS_BUCKET_NAMEが未設定のためGCS保存はスキップされます"}), 200

    try:
        from api.utils_image import _get_gcs_client
        client = _get_gcs_client()
        if not client:
            result["gcs_client"] = "❌ 初期化失敗（認証エラーの可能性）"
            return jsonify({"status": "error", "detail": result}), 500

        # バケットへの参照を取得（reload不要、オブジェクト操作で権限確認）
        bucket = client.bucket(bucket_name)
        result["bucket_name"] = bucket_name
        result["gcs_client"] = "✅ クライアント初期化OK"

        # テスト用の小さいファイルをアップロードして即削除
        import base64
        dummy = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
        test_blob = bucket.blob("atlas_health_test.png")
        test_blob.upload_from_string(dummy, content_type="image/png")
        test_blob.delete()
        result["write_test"] = "✅ アップロード・削除テスト成功"
        return jsonify({"status": "ok", "detail": result})
    except Exception as e:
        result["error"] = str(e)
        return jsonify({"status": "error", "detail": result}), 500


@app.route('/api/health/sheets-write', methods=['GET'])
def health_sheets_write():
    """Sheetsへの書き込みテスト（テスト行を追加して即削除）"""
    try:
        from api.utils_sheet import _get_worksheet, LOG_SHEET_NAME
        import datetime, uuid
        ws = _get_worksheet(LOG_SHEET_NAME)
        test_id = f"TEST-{uuid.uuid4().hex[:8]}"
        test_row = [
            test_id,
            datetime.datetime.utcnow().isoformat(),
            "テスト石",
            "", "", "", "", "", "", "", "", "", "", False,
        ]
        ws.append_row(test_row, value_input_option='USER_ENTERED')
        # 書き込んだ行を探して削除
        ids = ws.col_values(1)
        if test_id in ids:
            row_num = ids.index(test_id) + 1
            ws.delete_rows(row_num)
            return jsonify({"status": "ok", "message": "書き込み・削除テスト成功"})
        return jsonify({"status": "error", "message": "書き込み後に行が見つかりませんでした"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/health/sheets', methods=['GET'])
def health_sheets():
    """Google Sheets接続診断エンドポイント"""
    import os, json
    result = {}

    # 環境変数の存在確認
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "")
    sa_json  = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    result["GOOGLE_SHEET_ID"]              = sheet_id[:8] + "..." if sheet_id else "❌ 未設定"
    result["GOOGLE_SERVICE_ACCOUNT_JSON"]  = "✅ 設定あり" if sa_json else "❌ 未設定"

    if not sheet_id or not sa_json:
        return jsonify({"status": "error", "detail": result}), 500

    # サービスアカウントのメールアドレスを表示
    try:
        info = json.loads(sa_json)
        result["service_account_email"] = info.get("client_email", "不明")
    except Exception as e:
        result["service_account_email"] = f"JSON解析エラー: {e}"
        return jsonify({"status": "error", "detail": result}), 500

    # スプレッドシートへの接続テスト
    try:
        from api.utils_sheet import _get_worksheet, LOG_SHEET_NAME, ORDER_SHEET_NAME, PROFILE_SHEET_NAME
        sheets_status = {}
        for name in [LOG_SHEET_NAME, ORDER_SHEET_NAME, PROFILE_SHEET_NAME]:
            try:
                ws = _get_worksheet(name)
                headers = ws.row_values(1)
                sheets_status[name] = f"✅ 接続OK（{len(headers)}列）"
            except Exception as e:
                sheets_status[name] = f"❌ {e}"
        result["sheets"] = sheets_status
        all_ok = all("✅" in v for v in sheets_status.values())
        return jsonify({"status": "ok" if all_ok else "partial", "detail": result})
    except Exception as e:
        result["connection_error"] = str(e)
        return jsonify({"status": "error", "detail": result}), 500


@app.route('/admin')
def admin_page():
    """管理画面エントリポイント"""
    return app.send_static_file('admin.html')


# ===== 管理API =====

def _check_admin_auth() -> bool:
    """管理APIの認証チェック（ADMIN_PASSWORDと照合）"""
    import os
    admin_password = os.environ.get("ADMIN_PASSWORD", "")
    if not admin_password:
        return False
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        return token == admin_password
    # bodyにpasswordが含まれる場合も許可
    body = request.get_json(force=True, silent=True) or {}
    return body.get("password") == admin_password


@app.route('/api/admin/master', methods=['GET'])
def admin_get_master():
    """管理画面用：全マスターデータ（シート優先）＋現在のconfig設定を返す"""
    if not _check_admin_auth():
        return jsonify({"error": "認証が必要です"}), 401

    from api.stone_master import get_stone_master_data, get_stone
    from api.stone_combination_master import get_combination_master_data
    from api.product_master import get_product_master_data
    from api.matching import SCORE_WEIGHTS, get_score_weights

    # スコア重み（configオーバーライド反映済み）
    score_weights = get_score_weights()

    # 商品マスター（シート優先）
    products = []
    for pid, p in get_product_master_data().items():
        entry = dict(p)
        entry["product_id"] = pid
        entry["stone_names"] = [
            (get_stone(part["stone_id"]) or {}).get("stone_name", part["stone_id"])
            for part in entry["parts"]
        ]
        products.append(entry)

    # 石マスター（シート優先・表示用整形）
    stone_master = get_stone_master_data()
    stones = []
    for sid, s in stone_master.items():
        stones.append({
            "stone_id": sid,
            "stone_name": s["stone_name"],
            "description": s["description"],
            "element_profile": s["element_profile"],
            "theme_tags": s["theme_tags"],
            "worry_tags": s["worry_tags"],
            "weight": s.get("weight", 1.0),
        })

    # 組み合わせマスター（シート優先・frozensetをリストに変換）
    combinations = []
    for key, effect in get_combination_master_data().items():
        stone_ids = sorted(list(key))
        stone_names = [
            (stone_master.get(sid) or {}).get("stone_name", sid)
            for sid in stone_ids
        ]
        combinations.append({
            "stones": stone_ids,
            "stone_names": stone_names,
            "theme_tags": effect["theme_tags"],
            "worry_tags": effect["worry_tags"],
            "meaning": effect["meaning"],
            "weight": effect.get("weight", 1.0),
        })

    return jsonify({
        "score_weights": score_weights,
        "products": products,
        "stones": stones,
        "combinations": combinations,
    })


@app.route('/api/admin/config', methods=['POST'])
def admin_update_config():
    """管理画面用：config設定を更新する"""
    body = request.get_json(force=True, silent=True) or {}
    if not _check_admin_auth():
        return jsonify({"error": "認証が必要です"}), 401

    updates = body.get("updates", {})
    if not updates:
        return jsonify({"error": "updatesが空です"}), 400

    errors = []
    for key, value in updates.items():
        try:
            note = body.get("notes", {}).get(key, "")
            set_config(key, str(value), note)
        except Exception as e:
            logger.exception("config更新エラー: %s", key)
            errors.append({"key": key, "error": str(e)})

    if errors:
        return jsonify({"status": "partial", "errors": errors}), 207
    return jsonify({"status": "ok", "updated": list(updates.keys())})


@app.route('/api/admin/migrate-to-sheets', methods=['POST'])
def admin_migrate_to_sheets():
    """管理画面用：Pythonハードコードのマスターデータをシートに書き込む（初回移行）"""
    if not _check_admin_auth():
        return jsonify({"error": "認証が必要です"}), 401

    from api.stone_master import STONE_MASTER
    from api.stone_combination_master import STONE_COMBINATION_MASTER
    from api.product_master import PRODUCT_MASTER
    from api.utils_sheet import (
        write_stone_master_to_sheet,
        write_combination_master_to_sheet,
        write_product_master_to_sheet,
    )

    results = {}
    errors = []

    try:
        write_stone_master_to_sheet(STONE_MASTER)
        results["stone_master"] = f"✅ {len(STONE_MASTER)}件書き込み"
    except Exception as e:
        errors.append(f"石マスター: {e}")
        results["stone_master"] = "❌ 失敗"

    try:
        write_combination_master_to_sheet(STONE_COMBINATION_MASTER)
        results["stone_combinations"] = f"✅ {len(STONE_COMBINATION_MASTER)}件書き込み"
    except Exception as e:
        errors.append(f"組み合わせマスター: {e}")
        results["stone_combinations"] = "❌ 失敗"

    try:
        write_product_master_to_sheet(PRODUCT_MASTER)
        results["product_master"] = f"✅ {len(PRODUCT_MASTER)}件書き込み"
    except Exception as e:
        errors.append(f"商品マスター: {e}")
        results["product_master"] = "❌ 失敗"

    # 移行後にキャッシュをクリアしてシートから再読み込みさせる
    from api.stone_master import invalidate_stone_master_cache
    from api.stone_combination_master import invalidate_combination_master_cache
    from api.product_master import invalidate_product_master_cache
    invalidate_stone_master_cache()
    invalidate_combination_master_cache()
    invalidate_product_master_cache()

    status = "ok" if not errors else "partial"
    return jsonify({"status": status, "results": results, "errors": errors})


@app.route('/api/admin/clear-cache', methods=['POST'])
def admin_clear_cache():
    """管理画面用：全マスターキャッシュをクリアしてシートから再読み込みさせる"""
    if not _check_admin_auth():
        return jsonify({"error": "認証が必要です"}), 401

    from api.stone_master import invalidate_stone_master_cache
    from api.stone_combination_master import invalidate_combination_master_cache
    from api.product_master import invalidate_product_master_cache
    invalidate_stone_master_cache()
    invalidate_combination_master_cache()
    invalidate_product_master_cache()

    return jsonify({"status": "ok", "message": "全マスターキャッシュをクリアしました"})


@app.route('/')
def index():
    """フロントエンドのエントリポイント"""
    return app.send_static_file('index.html')


# ===== エラーハンドラー =====

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "ページが見つかりません"}), 404


@app.errorhandler(500)
def internal_error(e):
    logger.exception("Internal server error")
    return jsonify({"error": "サーバーエラーが発生しました"}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
