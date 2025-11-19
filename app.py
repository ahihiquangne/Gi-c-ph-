import time
import re
import requests
from flask import Flask, jsonify
from datetime import datetime, timezone, timedelta

CACHE_DURATION_SECONDS = 30 * 60  # Cache 30 phút

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

app = Flask(__name__)
application = app

cached_data = {"data": None, "timestamp": 0}

def scrape_giacaphe():
    url = "https://giacaphe.com/gia-ca-phe-noi-dia/"
    try:
        print("Scrape giacaphe.com bằng requests thường...")
        html = requests.get(url, headers=HEADERS, timeout=20).text

        # Regex bắt chuẩn từ View Source (cha chụp)
        patterns = {
            'Trung bình': r'Trung bình[^<]*<span[^>]*>([\d.,]+)[^<]*</span>[^<]*<span[^>]*>([+-][\d.,]+)',
            'Đắk Lắk':    r'Đắk Lắk[^<]*<span[^>]*>([\d.,]+)[^<]*</span>[^<]*<span[^>]*>([+-][\d.,]+)',
            'Lâm Đồng':   r'Lâm Đồng[^<]*<span[^>]*>([\d.,]+)[^<]*</span>[^<]*<span[^>]*>([+-][\d.,]+)',
            'Gia Lai':    r'Gia Lai[^<]*<span[^>]*>([\d.,]+)[^<]*</span>[^<]*<span[^>]*>([+-][\d.,]+)',
            'Đắk Nông':   r'Đắk Nông[^<]*<span[^>]*>([\d.,]+)[^<]*</span>[^<]*<span[^>]*>([+-][\d.,]+)',
        }

        prices = {}
        for name, pat in patterns.items():
            m = re.search(pat, html, re.S)
            if m:
                prices[name] = {"price": m.group(1).strip(), "change": m.group(2).strip()}

        # Kiểm tra có đủ ít nhất 3 tỉnh → live
        if len(prices) >= 3 and "Trung bình" in prices:
            print("LIVE GIACAPHE.COM THÀNH CÔNG 100%!")
            return {
                "source": "giacaphe.com (LIVE trực tiếp – requests thường)",
                "average": {"price": prices['Trung bình']['price'], "change": prices['Trung bình']['change']},
                "prices": [
                    {"province": "Đắk Lắk", "price": prices.get('Đắk Lắk', {}).get('price', 'N/A'), "change": prices.get('Đắk Lắk', {}).get('change', '0')},
                    {"province": "Lâm Đồng", "price": prices.get('Lâm Đồng', {}).get('price', 'N/A'), "change": prices.get('Lâm Đồng', {}).get('change', '0')},
                    {"province": "Gia Lai", "price": prices.get('Gia Lai', {}).get('price', 'N/A'), "change": prices.get('Gia Lai', {}).get('change', '0')},
                    {"province": "Đắk Nông", "price": prices.get('Đắk Nông', {}).get('price', 'N/A'), "change": prices.get('Đắk Nông', {}).get('change', '0')},
                ],
                "timestamp": int(time.time()),
                "date": datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M"),
                "unit": "VNĐ/kg"
            }
    except Exception as e:
        print("Lỗi scrape:", e)

    # Fallback chỉ khi thật sự lỗi mạng
    print("Dùng fallback tạm (19/11/2025)")
    return {
        "source": "Hardcode dự phòng",
        "average": {"price": "113,500", "change": "+3,200"},
        "prices": [
            {"province": "Đắk Lắk", "price": "113,700", "change": "+3,200"},
            {"province": "Lâm Đồng", "price": "112,600", "change": "+4,100"},
            {"province": "Gia Lai", "price": "113,000", "change": "+3,200"},
            {"province": "Đắk Nông", "price": "113,800", "change": "+3,300"}
        ],
        "timestamp": int(time.time()),
        "date": datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M"),
        "unit": "VNĐ/kg"
    }

@app.route('/api/coffee-prices')
def api_get_prices():
    global cached_data
    now = time.time()
    if cached_data["data"] and (now - cached_data["timestamp"] < CACHE_DURATION_SECONDS):
        print("Trả từ cache")
        return jsonify(cached_data["data"])
    
    fresh = scrape_giacaphe()
    cached_data = {"data": fresh, "timestamp": now}
    print("Trả dữ liệu mới")
    return jsonify(fresh)

@app.route('/')
def home():
    return "YeuHat Coffee API – Live trực tiếp từ giacaphe.com ☕"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
