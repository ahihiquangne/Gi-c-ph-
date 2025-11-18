import time
import re
import requests
from flask import Flask, jsonify
from datetime import datetime, timezone, timedelta

# --- SCRAPINGBEE KEY CỦA CHA ---
SCRAPINGBEE_KEY = "RX9G6Y1COPATUBC9AF2QDE411G66VVFI5G0EPUDE7VGGFULCRH2JTFZR9NL3WG6K8PZH9R5E40C4DWOS"

CACHE_DURATION_SECONDS = 35 * 60  # Cache 35 phút

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

app = Flask(__name__)
application = app

# ĐÃ FIX LỖI Ở ĐÂY
cached_data = {"data": None, "timestamp": 0}

def scrape_giacaphe_scrapingbee():
    target_url = "https://giacaphe.com/gia-ca-phe-noi-dia/"
    
    params = {
        'api_key': SCRAPINGBEE_KEY,
        'url': target_url,
        'render_js': 'true',
        'premium_proxy': 'true',
        'country_code': 'vn'
    }

    try:
        print("🔥 Đang scrape giacaphe.com bằng ScrapingBee...")
        response = requests.get('https://app.scrapingbee.com/api/v1/', params=params, headers=HEADERS, timeout=60)
        response.raise_for_status()
        html = response.text

        patterns = {
            'Trung bình': r'Trung bình\D*([\d.,]+)\D*([+-][\d.,]+)',
            'Đắk Lắk': r'Đắk Lắk\D*([\d.,]+)\D*([+-][\d.,]+)',
            'Lâm Đồng': r'Lâm Đồng\D*([\d.,]+)\D*([+-][\d.,]+)',
            'Gia Lili': r'Gia Lai\D*([\d.,]+)\D*([+-][\d.,]+)',
            'Đắk Nông': r'Đắk Nông\D*([\d.,]+)\D*([+-][\d.,]+)',
        }

        prices = {}
        for prov, pat in patterns.items():
            m = re.search(pat, html, re.S)
            if m:
                prices[prov] = {"price": m.group(1).strip(), "change": m.group(2).strip()}

        if "Đắk Lắk" in prices:
            print("🎉 LIVE GIACAPHE.COM THÀNH CÔNG!")
            return {
                "source": "giacaphe.com (LIVE via ScrapingBee)",
                "average": {"price": prices.get('Trung bình', {}).get('price', '113,500'), "change": prices.get('Trung bình', {}).get('change', '+3,200')},
                "prices": [
                    {"province": "Đắk Lắk", "price": prices['Đắk Lắk']['price'], "change": prices['Đắk Lắk']['change']},
                    {"province": "Lâm Đồng", "price": prices['Lâm Đồng']['price'], "change": prices['Lâm Đồng']['change']},
                    {"province": "Gia Lai", "price": prices['Gia Lai']['price'], "change": prices['Gia Lai']['change']},
                    {"province": "Đắk Nông", "price": prices['Đắk Nông']['price'], "change": prices['Đắk Nông']['change']},
                ],
                "timestamp": int(time.time()),
                "date": datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S"),
                "unit": "VNĐ/kg"
            }
    except Exception as e:
        print("Lỗi ScrapingBee:", str(e))

    # Fallback chuẩn ngày 19/11
    print("Dùng fallback tạm")
    return {
        "source": "Hardcode dự phòng (19/11/2025)",
        "average": {"price": "113,800", "change": "+3,300"},
        "prices": [
            {"province": "Đắk Lắk", "price": "114,000", "change": "+3,400"},
            {"province": "Lâm Đồng", "price": "112,800", "change": "+3,200"},
            {"province": "Gia Lai", "price": "113,700", "change": "+3,300"},
            {"province": "Đắk Nông", "price": "113,900", "change": "+3,300"}
        ],
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
    
    fresh = scrape_giacaphe_scrapingbee()
    cached_data["data"] = fresh
    cached_data["timestamp"] = now
    print("→ Trả dữ liệu mới")
    return jsonify(fresh)

@app.route('/')
def home():
    return "YeuHat Coffee API - Live via ScrapingBee ☕"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
