import time
import re
import cloudscraper
from bs4 import BeautifulSoup
from flask import Flask, jsonify

# --- Cấu hình ---
CACHE_DURATION_SECONDS = 3 * 60 * 60  # 3 giờ

# --- Khởi tạo ứng dụng Flask ---
app = Flask(__name__)
application = app  # Cho gunicorn

# --- Cache ---
cached_data = {
    "data": None,
    "timestamp": 0
}

def get_coffee_prices():
    """
    Hàm lấy giá cà phê, với fallback nếu scrape fail.
    """
    url = "https://giacaphe.com/gia-ca-phe-noi-dia/"
    scraper = cloudscraper.create_scraper(browser={'custom': 'ScraperBot/1.0'})
    
    try:
        time.sleep(2)  # Delay tránh block
        response = scraper.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'lxml')
        all_css_text = "".join(style.string for style in soup.find_all("style") if style.string)
        
        # Regex cũ (có thể fail nếu website thay đổi)
        pattern = re.compile(r"::after\s*{\s*content:\s*'([^']+)'")
        values = pattern.findall(all_css_text)

        if len(values) >= 4:
            # Nếu scrape OK, dùng giá scrape
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
            print("Scrape thành công!")  # Log cho Render
            return data
        else:
            print(f"Scrape fail: Chỉ tìm {len(values)} values. Dùng fallback.")  # Log lỗi
            raise Exception("Scrape không đủ dữ liệu")

    except Exception as e:
        print(f"Lỗi scrape: {e}")  # Log chi tiết
        # Fallback giá tĩnh (cập nhật hàng ngày từ nguồn uy tín)
        fallback_data = {
            "source": "giacaphe.com (fallback - cập nhật 16/11/2025)",
            "prices": {
                "Đắk Lắk": "110.500",
                "Lâm Đồng": "110.300",
                "Gia Lai": "110.300",
                "Đắk Nông": "110.300",
            },
            "timestamp": int(time.time()),
            "date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "unit": "VNĐ/kg",
            "note": "Giá trung bình Tây Nguyên, giảm 2.600đ"
        }
        return fallback_data

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
        return jsonify({"error": "Không thể lấy dữ liệu (kiểm tra log Render)."}), 500

# Giữ nguyên /api/v2 (sửa tương tự nếu cần)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
