import time
import re
import requests
from flask import Flask, jsonify
from datetime import datetime, timezone, timedelta

CACHE_DURATION_SECONDS = 30 * 60  # Cache 30 phút

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

app = Flask(__name__)
application = app

cached_data = {"data": None, "timestamp": 0}

def scrape_chocaphe():
    url = "https://chocaphe.vn/gia-ca-phe-truc-tuyen.cfp"  # Nguồn cha gửi – live 100%
    try:
        print("Scrape chocaphe.vn – giá cà phê trực tuyến...")
        html = requests.get(url, headers=HEADERS, timeout=20).text

        # Regex bắt chuẩn từ ảnh + HTML (Trung bình, tỉnh, thay đổi)
        patterns = {
            'Trung bình': r'Giá trung bình\D*([\d.,]+)\D*([+-][\d.,]+)',
            'Đắk Lắk': r'Đắk Lắk\D*([\d.,]+)\D*([+-][\d.,]+)',
            'Lâm Đồng': r'Lâm Đồng\D*([\d.,]+)\D*([+-][\d.,]+)',
            'Gia Lai': r'Gia Lai\D*([\d.,]+)\D*([+-][\d.,]+)',
            'Đắk Nông': r'Đắk Nông\D*([\d.,]+)\D*([+-][\d.,]+)',
            'Hồ tiêu': r'Hồ tiêu\D*([\d.,]+)\D*([+-][\d.,]+)',
            'USD/VND': r'Tỷ giá USD/VND\D*([\d.,]+)',
        }

        prices = {}
        for key, pat in patterns.items():
            m = re.search(pat, html, re.S | re.I)
            if m:
                prices[key] = {"price": m.group(1).strip(), "change": m.group(2).strip() if len(m.groups()) > 1 else '0'}

        if "Trung bình" in prices:
            print("LIVE THÀNH CÔNG TỪ CHOCAPHE.VN!")
            return {
                "source": "chocaphe.vn (LIVE trực tuyến – nguồn cha tìm)",
                "average": {"price": prices['Trung bình']['price'], "change": prices['Trung bình']['change']},
                "prices": [
                    {"province": "Đắk Lắk", "price": prices.get('Đắk Lắk', {}).get('price', 'N/A'), "change": prices.get('Đắk Lắk', {}).get('change', '0')},
                    {"province": "Lâm Đồng", "price": prices.get('Lâm Đồng', {}).get('price', 'N/A'), "change": prices.get('Lâm Đồng', {}).get('change', '0')},
                    {"province": "Gia Lai", "price": prices.get('Gia Lai', {}).get('price', 'N/A'), "change": prices.get('Gia Lai', {}).get('change', '0')},
                    {"province": "Đắk Nông", "price": prices.get('Đắk Nông', {}).get('price', 'N/A'), "change": prices.get('Đắk Nông', {}).get('change', '0')},
                ],
                "pepper": {"price": prices.get('Hồ tiêu', {}).get('price', 'N/A'), "change": prices.get('Hồ tiêu', {}).get('change', '0')},
                "exchange": {"usd_vnd": prices.get('USD/VND', {}).get('price', 'N/A')},
                "timestamp": int(time.time()),
                "date": datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S"),
                "unit": "VNĐ/kg"
            }
    except Exception as e:
        print("Lỗi scrape:", e)

    # Fallback chuẩn (cha có thể bỏ nếu muốn)
    print("Dùng fallback tạm")
    return {
        "source": "Hardcode dự phòng (07/12/2025)",
        "average": {"price": "103,900", "change": "+3,000"},
        "prices": [
            {"province": "Đắk Lắk", "price": "104,000", "change": "+4,000"},
            {"province": "Lâm Đồng", "price": "103,300", "change": "+5,000"},
            {"province": "Gia Lai", "price": "103,600", "change": "+4,000"},
            {"province": "Đắk Nông", "price": "104,000", "change": "+2,000"}
        ],
        "pepper": {"price": "148,500", "change": "-1,500"},
        "exchange": {"usd_vnd": "26,138"},
        "timestamp": int(time.time()),
        "date": datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S"),
        "unit": "VNĐ/kg"
    }

@app.route('/api/coffee-prices')
def api_get_prices():
    global cached_data
    now = time.time()
    if cached_data["data"] and (now - cached_data["timestamp"] < CACHE_DURATION_SECONDS):
        print("→ Trả từ cache")
        return jsonify(cached_data["data"])
    
    fresh = scrape_chocaphe()
    cached_data["data"] = fresh
    cached_data["timestamp"] = now
    print("→ Trả dữ liệu mới")
    return jsonify(fresh)

@app.route('/')
def home():
    return "YeuHat Coffee API – Live từ chocaphe.vn ☕"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
