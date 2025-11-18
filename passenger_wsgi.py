import time
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify

# --- Cấu hình ---
CACHE_DURATION_SECONDS = 3 * 60 * 60  # Lưu cache 3 tiếng
SCRAPER_API_KEY = "406d12726797254e25a327312ff5bf44"

# --- Khởi tạo ứng dụng Flask ---
app = Flask(__name__)
application = app  # Biến WSGI

# --- Biến toàn cục cache ---
cached_data = {"data": None, "timestamp": 0}


def get_coffee_prices():
    """
    Lấy giá cà phê từ giacaphe.com bằng ScraperAPI (bypass Cloudflare)
    """
    api_url = "https://api.scraperapi.com/"
    params = {
        "api_key": SCRAPER_API_KEY,
        "url": "https://giacaphe.com/gia-ca-phe-noi-dia/",
        "render": "html",
        "device_type": "desktop",
        "keep_headers": "true"
    }

    try:
        print("→ Gọi ScraperAPI...")
        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        html = response.text

        # Parse HTML
        soup = BeautifulSoup(html, "lxml")
        all_css_text = "".join(style.string for style in soup.find_all("style") if style.string)

        import re
        pattern = re.compile(r"::after\s*{\s*content:\s*'([^']+)'")
        values = pattern.findall(all_css_text)

        if len(values) < 4:
            print("⚠ Không tìm đủ dữ liệu CSS, fallback.")
            raise ValueError("CSS values not found")

        data = {
            "source": "giacaphe.com",
            "prices": {
                "Đắk Lắk": values[0],
                "Lâm Đồng": values[1],
                "Gia Lai": values[2],
                "Đắk Nông": values[3],
            },
            "timestamp": int(time.time()),
            "date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "text": f"Giá cà phê nội địa\nĐắk Lắk: {values[0]}\nLâm Đồng: {values[1]}\nGia Lai: {values[2]}\nĐắk Nông: {values[3]}",
            "unit": "VNĐ/kg"
        }
        print("→ Lấy dữ liệu thành công (ScraperAPI)")
        return data

    except Exception as e:
        print("⚠ SCRAPERAPI ERROR:", e)
        # Fallback cứng
        fallback_data = {
            "source": "giacaphe.com (fallback)",
            "prices": {
                "Đắk Lắk": "110,500",
                "Lâm Đồng": "108,700",
                "Gia Lai": "109,800",
                "Đắk Nông": "110,500",
            },
            "timestamp": int(time.time()),
            "date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "text": "Fallback giá cà phê nội địa",
            "unit": "VNĐ/kg"
        }
        return fallback_data


@app.route('/api/coffee-prices', methods=['GET'])
def api_get_prices():
    global cached_data
    current_time = time.time()

    # Kiểm tra cache
    if cached_data["data"] and (current_time - cached_data["timestamp"] < CACHE_DURATION_SECONDS):
        return jsonify(cached_data["data"])

    fresh_data = get_coffee_prices()
    cached_data["data"] = fresh_data
    cached_data["timestamp"] = current_time
    return jsonify(fresh_data)


@app.route('/api/v2/coffee-prices', methods=['GET'])
def api_v2_get_prices():
    """
    API V2: Trả về danh sách provinceId, provinceName, price
    """
    global cached_data
    current_time = time.time()

    if cached_data["data"] and (current_time - cached_data["timestamp"] < CACHE_DURATION_SECONDS):
        data = cached_data["data"]
    else:
        data = get_coffee_prices()
        cached_data["data"] = data
        cached_data["timestamp"] = current_time

    try:
        mapping = [
            {"provinceId": 1, "provinceName": "Đắk Lắk",
             "price": int(data["prices"]["Đắk Lắk"].replace('.', '').replace(',', ''))},
            {"provinceId": 2, "provinceName": "Lâm Đồng",
             "price": int(data["prices"]["Lâm Đồng"].replace('.', '').replace(',', ''))},
            {"provinceId": 3, "provinceName": "Gia Lai",
             "price": int(data["prices"]["Gia Lai"].replace('.', '').replace(',', ''))},
            {"provinceId": 4, "provinceName": "Đắk Nông",
             "price": int(data["prices"]["Đắk Nông"].replace('.', '').replace(',', ''))},
        ]
    except Exception as e:
        print("⚠ Lỗi convert price:", e)
        mapping = []

    return jsonify({
        "source": data.get("source", ""),
        "timestamp": data.get("timestamp", 0),
        "date": data.get("date", ""),
        "unit": data.get("unit", ""),
        "prices": mapping
    })


@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Coffee Price API - dùng /api/coffee-prices hoặc /api/v2/coffee-prices"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
