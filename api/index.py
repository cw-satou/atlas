from flask import Flask, request, jsonify
import os
import logging

from api.diagnose import diagnose, build_bracelet
from api.utils_sheet import get_diagnosis, upsert_profile, get_profile
from api.utils_perplexity import generate_today_fortune
from api.woo_webhook import woo_webhook

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='public', static_url_path='')


# ===== 診断関連ルート =====

@app.route('/api/diagnose', methods=['POST'])
def route_diagnose():
    """占い診断（第1フェーズ：エレメント＆メインストーン選定）"""
    return diagnose()


@app.route('/api/build-bracelet', methods=['POST'])
def route_build_bracelet():
    """ブレスレット生成（第2フェーズ：サイズ＆デザイン決定）"""
    return build_bracelet()


@app.route('/api/fortune-detail', methods=['POST'])
def fortune_detail():
    """保存済み診断結果の詳細取得"""
    data = request.get_json(force=True, silent=True) or {}
    diagnosis_id = data.get("diagnosis_id")

    if not diagnosis_id:
        return jsonify({"error": "diagnosis_id is required"}), 400

    saved = get_diagnosis(diagnosis_id)
    if not saved:
        return jsonify({"error": "Diagnosis not found"}), 404

    base_url = os.environ.get("SHOP_BASE_URL", "").strip()
    if not base_url:
        base_url = "https://yourshop.com/product/"

    # 3商品バリエーション生成（top / single / double）
    product_slug_top = saved.get("product_slug") or "top-crystal"
    if not product_slug_top.startswith("top-"):
        product_slug_top = "top-" + product_slug_top

    product_slug_single = product_slug_top.replace("top-", "single-", 1)
    product_slug_double = product_slug_top.replace("top-", "double-", 1)

    product_urls = {
        "top": base_url + product_slug_top,
        "single": base_url + product_slug_single,
        "double": base_url + product_slug_double,
    }

    response = {
        "diagnosis_id": saved.get("diagnosis_id"),
        "stone_name": saved.get("stone_name"),
        "past": saved.get("past"),
        "present": saved.get("present"),
        "future": saved.get("future"),
        "element_detail": saved.get("element_detail"),
        "oracle_name": saved.get("oracle_name"),
        "oracle_position": saved.get("oracle_position"),
        "product_urls": product_urls,
    }

    return jsonify(response)


@app.route("/api/today-fortune", methods=["POST"])
def today_fortune():
    """今日の運勢API（生年月日・出生時間・出生地ベース）"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        message = generate_today_fortune(data)
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
            return jsonify({"error": "user_id is required"}), 400
        try:
            upsert_profile(body)
            profile = get_profile(user_id)
            return jsonify(profile or {})
        except Exception as e:
            logger.exception("プロフィール保存エラー")
            return jsonify({"error": "Failed to save profile"}), 500

    # GET
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    try:
        profile = get_profile(user_id)
        if not profile:
            return jsonify({"error": "not found"}), 404
        return jsonify(profile)
    except Exception as e:
        logger.exception("プロフィール取得エラー")
        return jsonify({"error": "Failed to load profile"}), 500


# ===== ヘルスチェック & フロントエンド =====

@app.route('/api/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "ok", "service": "星の羅針盤 API"})


@app.route('/')
def index():
    """フロントエンドのエントリポイント"""
    return app.send_static_file('index.html')


# ===== エラーハンドラー =====

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    logger.exception("Internal server error")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
