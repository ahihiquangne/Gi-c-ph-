import time
import re
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, send_from_directory

# --- Cấu hình ---
CACHE_DURATION_SECONDS = 3 * 60 * 60  # 3 giờ
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'vi-VN,vi;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# --- Khởi tạo ứng dụng Flask ---
app = Flask(__name__)
application = app

# --- Cache ---
cached_data = {
    "data": None,
    "timestamp": 0
}

def get_coffee_prices():
    """
    Lấy giá cà phê bằng requests (thay cloudscraper để tránh 403).
    Fallback nếu fail.
    """
    url = "https://giacaphe.com/gia-ca-phe-noi-dia/"
    
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        time.sleep(3)  # Delay lớn hơn
        response = session.get(url)
        response.raise_for_status()  # Raise nếu 403/500
        
        soup = BeautifulSoup(response.text, 'lxml')
        all_css_text = "".join(style.string for style in soup.find_all("style") if style.string)
        
        # Regex CSS ::after (nếu website vẫn dùng)
        pattern = re.compile(r"::after\s*{\s*content:\s*'([^']+)'")
        values = pattern.findall(all_css_text)

        if len(values) >= 4:
            print("Scrape thành công bằng requests!")  # Log Render
            data = {
                "source": "giacaphe.com (scrape)",
                "prices": {
                    "Đắk Lắk": values[0],
                    "Lâm Đồng": values[1],
                    "Gia Lai": values[2],
                    "Đắk Nông": values[3],
                },
                "timestamp": int(time.time()),
                "date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "unit": "VNĐ/kg"
            }
            return data
        else:
            print(f"Scrape fail: Chỉ {len(values)} values. Dùng fallback.")
            raise Exception("Không đủ dữ liệu scrape")

    except Exception as e:
        print(f"Lỗi scrape: {e} (có thể 403 block). Dùng fallback.")
        # Fallback động (cập nhật từ nguồn uy tín hôm nay)
        fallback_data = {
            "source": "giacaphe.com (fallback - 16/11/2025)",
            "prices": {
                "Đắk Lắk": "110.500",
                "Lâm Đồng": "110.300",
                "Gia Lai": "110.300",
                "Đắk Nông": "110.300",
            },
            "timestamp": int(time.time()),
            "date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "unit": "VNĐ/kg",
            "note": "Trung bình Tây Nguyên giảm 2.600đ"
        }
        return fallback_data

@app.route('/', methods=['GET'])
def home():
    """Route root để tránh 404."""
    return jsonify({"message": "Coffee Price API - Sử dụng /api/coffee-prices"})

@app.route('/favicon.ico', methods=['GET'])
def favicon():
    """Tránh 404 favicon."""
    return send_from_directory('.', 'favicon.ico'), 204  # Hoặc return '', 204

@app.route('/api/coffee-prices', methods=['GET'])
def api_get_prices():
    global cached_data
    current_time = time.time()

    if cached_data["data"] and (current_time - cached_data["timestamp"] < CACHE_DURATION_SECONDS):
        print("Trả từ cache.")
        return jsonify(cached_data["data"])

    fresh_data = get_coffee_prices()
    
    # Luôn trả data (fallback đảm bảo không None)
    cached_data["data"] = fresh_data
    cached_data["timestamp"] = current_time
    print("Trả dữ liệu mới.")
    return jsonify(fresh_data)

@app.route('/api/v2/coffee-prices', methods=['GET'])
def api_v2_get_prices():
    # Tương tự, dùng fresh_data từ get_coffee_prices()
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

    def safe_int_price(price_str):
        try:
            return int(price_str.replace('.', '').replace(',', ''))
        except ValueError:
            return 0

    mapping = [
        {"provinceId": 1, "provinceName": "Đắk Lắk", "price": safe_int_price(data["prices"]["Đắk Lắk"])},
        {"provinceId": 2, "provinceName": "Lâm Đồng", "price": safe_int_price(data["prices"]["Lâm Đồng"])},
        {"provinceId": 3, "provinceName": "Gia Lai", "price": safe_int_price(data["prices"]["Gia Lai"])},
        {"provinceId": 4, "provinceName": "Đắk Nông", "price": safe_int_price(data["prices"]["Đắk Nông"])},
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
