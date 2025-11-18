import time
import requests
from flask import Flask, jsonify

# --- Cấu hình ---
CACHE_DURATION_SECONDS = 3 * 60 * 60  # 3 giờ
SCRAPER_API_KEY = "406d12726797254e25a327312ff5bf44"  # Thay bằng API key của bạn
TARGET_URL = "https://giacaphe.com/gia-ca-phe-noi-dia/"

# --- Khởi tạo Flask ---
app = Flask(__name__)
application = app  # WSGI compatible

# --- Cache toàn cục ---
cached_data = {
    "data": None,
    "timestamp": 0
}

def get_coffee_prices():
    """
    Lấy dữ liệu giá cà phê bằng ScraperAPI.
    """
    try:
        payload = {
            "api_key": SCRAPER_API_KEY,
            "url": TARGET_URL
        }
        r = requests.get("https://api.scraperapi.com/", params=payload, timeout=15)
        r.raise_for_status()
        text = r.text

        # Parse giá cà phê từ HTML bằng regex
        import re
        pattern = re.compile(r"([Đắk Lắk|Trung bình|Đắk Nông|Gia Lai|Lâm Đồng])\s*[:\-]?\s*(\d{3}(?:,\d{3})*)", re.IGNORECASE)
        matches = pattern.findall(text)

        if len(matches) < 4:
            return None  # Không đủ dữ liệu

        prices_dict = {m[0].strip(): m[1].replace(',', '') for m in matches}

        data = {
            "source": "giacaphe.com via ScraperAPI",
            "average": {"price": prices_dict.get("Trung bình", "N/A")},
            "prices": [
                {"province": "Đắk Lắk", "price": prices_dict.get("Đắk Lắk", "N/A")},
                {"province": "Lâm Đồng", "price": prices_dict.get("Lâm Đồng", "N/A")},
                {"province": "Gia Lai", "price": prices_dict.get("Gia Lai", "N/A")},
                {"province": "Đắk Nông", "price": prices_dict.get("Đắk Nông", "N/A")},
            ],
            "timestamp": int(time.time()),
            "date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "unit": "VNĐ/kg"
        }
        return data

    except Exception as e:
        print(f"Lỗi khi lấy dữ liệu từ ScraperAPI: {e}")
        return None

@app.route('/api/coffee-prices', methods=['GET'])
def api_get_prices():
    global cached_data
    current_time = time.time()

    if cached_data["data"] and (current_time - cached_data["timestamp"] < CACHE_DURATION_SECONDS):
        return jsonify(cached_data["data"])

    fresh_data = get_coffee_prices()
    if fresh_data:
        cached_data["data"] = fresh_data
        cached_data["timestamp"] = current_time
        return jsonify(fresh_data)
    else:
        return jsonify({"error": "Không thể lấy được dữ liệu giá cà phê."}), 500

@app.route('/api/v2/coffee-prices', methods=['GET'])
def api_v2_get_prices():
    global cached_data
    current_time = time.time()

    if cached_data["data"] and (current_time - cached_data["timestamp"] < CACHE_DURATION_SECONDS):
        data = cached_data["data"]
    else:
        data = get_coffee_prices()
        if not data:
            return jsonify({"error": "Không thể lấy dữ liệu."}), 500
        cached_data["data"] = data
        cached_data["timestamp"] = current_time

    mapping = [
        {"provinceId": 1, "provinceName": "Đắk Lắk", "price": int(data["prices"][0]["price"])},
        {"provinceId": 2, "provinceName": "Lâm Đồng", "price": int(data["prices"][1]["price"])},
        {"provinceId": 3, "provinceName": "Gia Lai", "price": int(data["prices"][2]["price"])},
        {"provinceId": 4, "provinceName": "Đắk Nông", "price": int(data["prices"][3]["price"])},
    ]

    return jsonify({
        "source": data["source"],
        "timestamp": data["timestamp"],
        "date": data["date"],
        "unit": data["unit"],
        "prices": mapping
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
