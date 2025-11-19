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

        # Regex mới linh hoạt hơn - bắt giá theo cấu trúc bảng <td> giacaphe.com 19/11/2025
        patterns = {
            'Trung bình': r'<td[^>]*>Trung bình[^<]*</td>\s*<td[^>]*>([\d,]{5,})\s*\(([-+]?\d{1,4})\)</td>',
            'Đắk Lắk': r'<td[^>]*>Đắk Lắk[^<]*</td>\s*<td[^>]*>([\d,]{5,})\s*\(([-+]?\d{1,4})\)</td>',
            'Lâm Đồng': r'<td[^>]*>Lâm Đồng[^<]*</td>\s*<td[^>]*>([\d,]{5,})\s*\(([-+]?\d{1,4})\)</td>',
            'Gia Lai': r'<td[^>]*>Gia Lai[^<]*</td>\s*<td[^>]*>([\d,]{5,})\s*\(([-+]?\d{1,4})\)</td>',
            'Đắk Nông': r'<td[^>]*>Đắk Nông[^<]*</td>\s*<td[^>]*>([\d,]{5,})\s*\(([-+]?\d{1,4})\)</td>',
        }

        prices = {}
        for prov, pat in patterns.items():
            m = re.search(pat, html, re.S | re.I)
            if m:
                price = m.group(1).strip().replace(',', '')  # Loại bỏ dấu phẩy, ví dụ "113,500" → 113500
                change = m.group(2).strip() if m.group(2) else '0'
                prices[prov] = {"price": price, "change": change}
            else:
                prices[prov] = {"price": "N/A", "change": "0"}

        # Chỉ fallback nếu thiếu quá nhiều tỉnh (ví dụ <3 tỉnh)
        if len([p for p in prices if prices[p]['price'] != 'N/A']) < 3:
            raise Exception("Scrape thiếu dữ liệu")

        print("🎉 LIVE GIACAPHE.COM THÀNH CÔNG - Đủ tỉnh!")
        avg_price = prices.get('Trung bình', {}).get('price', '113500')
        avg_change = prices.get('Trung bình', {}).get('change', '+3200')
        return {
            "source": "giacaphe.com (LIVE via ScrapingBee FREE)",
            "average": {"price": f"{int(avg_price):,}", "change": f"+{int(avg_change)}" if avg_change != '0' else avg_change},
            "prices": [
                {"province": "Đắk Lắk", "price": f"{int(prices['Đắk Lắk']['price']):,}" if prices['Đắk Lắk']['price'] != 'N/A' else "N/A", "change": prices['Đắk Lắk']['change']},
                {"province": "Lâm Đồng", "price": f"{int(prices['Lâm Đồng']['price']):,}" if prices['Lâm Đồng']['price'] != 'N/A' else "N/A", "change": prices['Lâm Đồng']['change']},
                {"province": "Gia Lai", "price": f"{int(prices['Gia Lai']['price']):,}" if prices['Gia Lai']['price'] != 'N/A' else "N/A", "change": prices['Gia Lai']['change']},
                {"province": "Đắk Nông", "price": f"{int(prices['Đắk Nông']['price']):,}" if prices['Đắk Nông']['price'] != 'N/A' else "N/A", "change": prices['Đắk Nông']['change']},
            ],
            "timestamp": int(time.time()),
            "date": datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S"),
            "unit": "VNĐ/kg"
        }
    except Exception as e:
        print("Lỗi ScrapingBee:", str(e))

    # Fallback an toàn
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
