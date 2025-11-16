import time
import re
import cloudscraper
from bs4 import BeautifulSoup
from flask import Flask, jsonify

# --- Cấu hình ---
CACHE_DURATION_SECONDS = 3 * 60 * 60  # 3 giờ

# --- Khởi tạo ứng dụng Flask ---
app = Flask(__name__)
application = app  # Cho gunicorn app:application trên Render

# --- Cache ---
cached_data = {
    "data": None,
    "timestamp": 0
}

def get_coffee_prices():
    """
    Hàm lấy giá cà phê từ giacaphe.com bằng scrape.
    """
    url = "https://giacaphe.com/gia-ca-phe-noi-dia/"
    scraper = cloudscraper.create_scraper(browser={'custom': 'ScraperBot/1.0'})
    
    try:
        # Thêm delay để tránh block
        time.sleep(2)
        response = scraper.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'lxml')
        all_css_text = "".join(style.string for style in soup.find_all("style") if style.string)
        
        pattern = re.compile(r"::after\s*{\s*content:\s*'([^']+)'")
        values = pattern.findall(all_css_text)

        if len(values) < 4:
            return None

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
            "text": "Giá cà phê nội địa \n" + 
            "Đắk Lắk: " + values[0] + "\n" +
            "Lâm Đồng: " + values[1] + "\n" +
            "Gia Lai: " + values[2] + "\n" +
            "Đắk Nông: " + values[3] + "",
            "unit": "VNĐ/kg"
        }
        return data

    except Exception as e:
        print(f"Lỗi khi lấy dữ liệu: {e}")
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
        return jsonify({"error": "Không thể lấy được dữ liệu giá cà phê."}), 500

@app.route('/api/v2/coffee-prices', methods=['GET'])
def api_v2_get_prices():
    """API V2: Trả mảng province với price int."""
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
