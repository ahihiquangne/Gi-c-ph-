import time
import re
import requests
from flask import Flask, jsonify

# --- Cấu hình ---
CACHE_DURATION_SECONDS = 3 * 60 * 60  # Cache 3 giờ
SCRAPERAPI_KEY = "406d12726797254e25a327312ff5bf44"  # Thay bằng API key của bạn

# --- Khởi tạo Flask ---
app = Flask(__name__)
application = app  # Biến tương thích WSGI

# --- Cache ---
cached_data = {
    "data": None,
    "timestamp": 0
}

def get_coffee_prices():
    """
    Lấy dữ liệu giá cà phê từ giacaphe.com qua ScraperAPI
    """
    url = "https://giacaphe.com/gia-ca-phe-noi-dia/"
    params = {
        "api_key": SCRAPERAPI_KEY,
        "url": url
    }

    try:
        response = requests.get("https://api.scraperapi.com/", params=params)
        response.raise_for_status()

        text = response.text

        # Regex lấy giá các tỉnh: Đắk Lắk, Lâm Đồng, Gia Lai, Đắk Nông
        pattern = re.compile(r'([Đắk Lắk|Lâm Đồng|Gia Lai|Đắk Nông]+)\s*[:\-]?\s*([\d,.]+)')
        matches = pattern.findall(text)

        if len(matches) < 4:
            return None  # Không đủ dữ liệu

        prices = {province.strip(): price.replace(",", "") for province, price in matches[:4]}

        data = {
            "source": "giacaphe.com (via ScraperAPI)",
            "prices": {
                "Đắk Lắk": prices.get("Đắk Lắk", "N/A"),
                "Lâm Đồng": prices.get("Lâm Đồng", "N/A"),
                "Gia Lai": prices.get("Gia Lai", "N/A"),
                "Đắk Nông": prices.get("Đắk Nông", "N/A"),
            },
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

    # Kiểm tra cache
    if cached_data["data"] and (current_time - cached_data["timestamp"] < CACHE_DURATION_SECONDS):
        return jsonify(cached_data["data"])

    # Lấy dữ liệu mới
    fresh_data = get_coffee_prices()
    if fresh_data:
        cached_data["data"] = fresh_data
        cached_data["timestamp"] = current_time
        return jsonify(fresh_data)
    else:
        return jsonify({"error": "Không thể lấy dữ liệu giá cà phê."}), 500

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
        {"provinceId": 1, "provinceName": "Đắk Lắk", "price": int(data["prices"]["Đắk Lắk"])},
        {"provinceId": 2, "provinceName": "Lâm Đồng", "price": int(data["prices"]["Lâm Đồng"])},
        {"provinceId": 3, "provinceName": "Gia Lai", "price": int(data["prices"]["Gia Lai"])},
        {"provinceId": 4, "provinceName": "Đắk Nông", "price": int(data["prices"]["Đắk Nông"])},
    ]

    return jsonify({
        "source": data["source"],
        "timestamp": data["timestamp"],
        "date": data["date"],
        "unit": data["unit"],
        "prices": mapping
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
