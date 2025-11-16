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
    Scrape toàn bộ dữ liệu từ giacaphe.com: trung bình, giá tỉnh + thay đổi, hồ tiêu, tỷ giá.
    Parse từ text HTML. Fallback nếu fail.
    """
    url = "https://giacaphe.com/gia-ca-phe-noi-dia/"
    
    for attempt in range(2):  # Retry 2 lần
        try:
            session = requests.Session()
            session.headers.update(HEADERS)
            time.sleep(3)  # Delay
            response = session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            full_text = soup.get_text()  # Lấy toàn bộ text để parse
            
            # Regex để extract giá + thay đổi (pattern linh hoạt cho text như "Đắk Lắk: 110,500 (-2,500)")
            pattern_price = re.compile(r'([Đắk Lắk|Trung bình|Đắk Nông|Gia Lai|Lâm Đồng])\s*[:\-]?\s*(\d{3}(?:,\d{3})*)\s*(\([+-]?\d{1,3}(?:,\d{3})*\))?', re.IGNORECASE)
            matches = pattern_price.findall(full_text)
            
            # Extract hồ tiêu và tỷ giá
            pepper_match = re.search(r'Hồ tiêu\s*[:\-]?\s*(\d{3}(?:,\d{3})*)\s*(\([+-]?\d{1,3}(?:,\d{3})*\))?', full_text)
            exchange_match = re.search(r'Tỷ giá USD/VND\s*[:\-]?\s*(\d{2,3}(?:,\d{3})*)', full_text)
            
            # Xử lý matches thành dict (nếu đủ dữ liệu)
            prices = {}
            changes = {}
            for match in matches:
                province = match[0].strip()
                price = match[1].strip().replace(',', '') if match[1] else 'N/A'
                change = match[2].strip('()') if match[2] else '0'
                prices[province] = f"{int(price):,}" if price != 'N/A' else 'N/A'
                changes[province] = change
            
            if len(prices) >= 4:  # Nếu scrape đủ (Trung bình + 4 tỉnh)
                print("Scrape toàn bộ thành công!")  # Log Render
                data = {
                    "source": "giacaphe.com (scrape full)",
                    "average": {"price": prices.get("Trung bình", "N/A"), "change": changes.get("Trung bình", "0")},
                    "prices": [
                        {"province": "Đắk Lắk", "price": prices.get("Đắk Lắk", "N/A"), "change": changes.get("Đắk Lắk", "0")},
                        {"province": "Lâm Đồng", "price": prices.get("Lâm Đồng", "N/A"), "change": changes.get("Lâm Đồng", "0")},
                        {"province": "Gia Lai", "price": prices.get("Gia Lai", "N/A"), "change": changes.get("Gia Lai", "0")},
                        {"province": "Đắk Nông", "price": prices.get("Đắk Nông", "N/A"), "change": changes.get("Đắk Nông", "0")}
                    ],
                    "pepper": {"price": pepper_match.group(1).strip().replace(',', '') if pepper_match else "N/A", 
                               "change": pepper_match.group(2).strip('()') if pepper_match and pepper_match.group(2) else "0"},
                    "exchange": {"usd_vnd": exchange_match.group(1).strip().replace(',', '') if exchange_match else "N/A"},
                    "timestamp": int(time.time()),
                    "date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                    "unit": "VNĐ/kg (tỷ giá: VND/USD)"
                }
                return data
            else:
                print(f"Scrape partial: Chỉ {len(prices)} items. Retry {attempt+1}/2.")
                time.sleep(2)
                continue
        
        except Exception as e:
            print(f"Lỗi scrape attempt {attempt+1}: {e}")
            continue
    
    # Fallback từ hình ảnh bạn (cập nhật 16/11/2025)
    print("Dùng fallback từ screenshot.")
    fallback_data = {
        "source": "giacaphe.com (fallback từ screenshot 16/11/2025)",
        "average": {"price": "110,300", "change": "-2,600"},
        "prices": [
            {"province": "Đắk Lắk", "price": "110,500", "change": "-2,500"},
            {"province": "Lâm Đồng", "price": "108,700", "change": "-2,300"},
            {"province": "Gia Lai", "price": "109,800", "change": "-2,700"},
            {"province": "Đắk Nông", "price": "110,500", "change": "-2,500"}
        ],
        "pepper": {"price": "145,000", "change": "+2"},
        "exchange": {"usd_vnd": "26,128"},
        "timestamp": int(time.time()),
        "date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "unit": "VNĐ/kg (tỷ giá: VND/USD)",
        "note": "Nguồn: giacaphe.com & giauet.com (Vietcombank)"
    }
    return fallback_data

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Coffee Price API Full - Sử dụng /api/coffee-prices"})

@app.route('/favicon.ico', methods=['GET'])
def favicon():
    return '', 204

@app.route('/api/coffee-prices', methods=['GET'])
def api_get_prices():
    global cached_data
    current_time = time.time()

    if cached_data["data"] and (current_time - cached_data["timestamp"] < CACHE_DURATION_SECONDS):
        print("Trả từ cache.")
        return jsonify(cached_data["data"])

    fresh_data = get_coffee_prices()
    
    cached_data["data"] = fresh_data
    cached_data["timestamp"] = current_time
    print("Trả dữ liệu đầy đủ mới.")
    return jsonify(fresh_data)

# Giữ /api/v2 nếu cần, nhưng giờ /api/coffee-prices đã full

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
