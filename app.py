import time
import re
import requests
from flask import Flask, jsonify
from datetime import datetime, timezone, timedelta

SCRAPINGBEE_KEY = "RX9G6Y1COPATUBC9AF2QDE411G66VVFI5G0EPUDE7VGGFULCRH2JTFZR9NL3WG6K8PZH9R5E40C4DWOS"

CACHE_DURATION_SECONDS = 35 * 60

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

app = Flask(__name__)
application = app

cached_data = {"data": None, "timestamp": 0}

def scrape_giacaphe_scrapingbee():
    target_url = "https://giacaphe.com/gia-ca-phe-noi-dia/"
    
    params = {
        'api_key': SCRAPINGBEE_KEY,
        'url': target_url,
        'render_js': 'true',
        'country_code': 'vn'
    }

    try:
        print("🔥 Scrape giacaphe.com bằng ScrapingBee FREE...")
        response = requests.get('https://app.scrapingbee.com/api/v1/', params=params, headers=HEADERS, timeout=60)
        response.raise_for_status()
        html = response.text

        patterns = {
            'Trung bình': r'Trung bình\D*([\d.,]+)\D*([+-][\d.,]+)',
            'Đắk Lắk': r'Đắk Lắk\D*([\d.,]+)\D*([+-][\d.,]+)',
            'Lâm Đồng': r'Lâm Đồng\D*([\d.,]+)\D*([+-][\d.,]+)',
            'Gia Lai': r'Gia Lai\D*([\d.,]+)\D*([+-][\d.,]+)',
            'Đắk Nông': r'Đắk Nông\D*([\d.,]+)\D*([+-][\d.,]+)',
        }

        prices = {}
        for prov, pat in patterns.items():
            m = re.search(pat, html, re.S)
            if m:
                prices[prov] = {"price": m.group(1).strip(), "change": m.group(2).strip() if len(m.groups()) > 1 else '0'}
            else:
                prices[prov] = {"price": "N/A", "change": "0"}  # Fallback cho tỉnh thiếu

        print("🎉 LIVE GIACAPHE.COM THÀNH CÔNG VỚI SCRAPINGBEE FREE!")  # Luôn in nếu scrape OK
        avg_price = prices.get('Trung bình', {}).get('price', '113,500')
        avg_change = prices.get('Trung bình', {}).get('change', '+3,200')
        return {
            "source": "giacaphe.com (LIVE via ScrapingBee FREE)",
            "average": {"price": avg_price, "change": avg_change},
            "prices": [
                {"province": "Đắk Lắk", "price": prices.get('Đắk Lắk', {}).get('price', 'N/A'), "change": prices.get('Đắk Lắk', {}).get('change', '0')},
                {"province": "Lâm Đồng", "price": prices.get('Lâm Đồng', {}).get('price', 'N/A'), "change": prices.get('Lâm Đồng', {}).get('change', '0')},
                {"province": "Gia Lai", "price": prices.get('Gia Lai', {}).get('price', 'N/A'), "change": prices.get('Gia Lai', {}).get('change', '0')},
                {"province": "Đắk Nông", "price": prices.get('Đắk Nông', {}).get('price', 'N/A'), "change": prices.get('Đắk Nông', {}).get('change', '0')},
            ],
            "timestamp": int(time.time()),
            "date": datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S"),
            "unit": "VNĐ/kg"
        }
    except Exception as e:
        print("Lỗi ScrapingBee:", str(e))
        raise  # Để fallback xử lý

    # Fallback chỉ khi scrape fail hoàn toàn
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
    return "YeuHat Coffee API - Live via ScrapingBee FREE ☕"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
