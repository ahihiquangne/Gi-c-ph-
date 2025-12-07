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
    url = "https://chocaphe.vn/gia-ca-phe-truc-tuyen.cfp"
    try:
        print("Scrape chocaphe.vn – giá cà phê trực tuyến...")
        html = requests.get(url, headers=HEADERS, timeout=20).text

        print("HTML scraped (for debug):", html)  # In HTML để debug lý do fail

        # Regex mới – bắt chuẩn định dạng chocaphe.vn từ tool
        patterns = {
            'Trung bình': r'Giá trung bình\D*([\d,]{5,})\D*([+-]\d{1,3}[,\.]?\d*)',
            'Đắk Lắk': r'Đắk Lắk\D*([\d,]{5,})\D*([+-]\d{1,3}[,\.]?\d*)',
            'Lâm Đồng': r'Lâm Đồng\D*([\d,]{5,})\D*([+-]\d{1,3}[,\.]?\d*)',
            'Gia Lai': r'Gia Lai\D*([\d,]{5,})\D*([+-]\d{1,3}[,\.]?\d*)',
            'Đắk Nông': r'Đắk Nông\D*([\d,]{5,})\D*([+-]\d{1,3}[,\.]?\d*)',
            'Hồ tiêu': r'Hồ tiêu\D*([\d,]{5,})\D*([+-]\d{1,3}[,\.]?\d*)',
            'USD/VND': r'Tỷ giá USD/VND\D*([\d,]{5,})',
        }

        prices = {}
        for key, pat in patterns.items():
            m = re.search(pat, html, re.S | re.I)
            if m:
                price = m.group(1).strip().replace(',', '')  # "103,900" → 103900
                change = m.group(2).strip() if len(m.groups()) > 1 else '0'
                prices[key] = {"price": price, "change": change}
            else:
                prices[key] = {"price": "N/A", "change": "0"}  # Log N/A để debug tỉnh nào miss

        print("Dữ liệu scraped (for debug):", prices)  # In prices để debug regex

        # Kiểm tra đủ tỉnh → live
        if "Trung bình" in prices and len(prices) >= 5:
            print("LIVE THÀNH CÔNG TỪ CHOCAPHE.VN!")
            return {
                "source": "chocaphe.vn (LIVE trực tuyến – nguồn cha tìm)",
                "average": {"price": f"{int(prices['Trung bình']['price']):,}", "change": prices['Trung bình']['change']},
                "prices": [
                    {"province": "Đắk Lắk", "price": f"{int(prices['Đắk Lắk']['price']):,}", "change": prices['Đắk Lắk']['change']},
                    {"province": "Lâm Đồng", "price": f"{int(prices['Lâm Đồng']['price']):,}", "change": prices['Lâm Đồng']['change']},
                    {"province": "Gia Lai", "price": f"{int(prices['Gia Lai']['price']):,}", "change": prices['Gia Lai']['change']},
                    {"province": "Đắk Nông", "price": f"{int(prices['Đắk Nông']['price']):,}", "change": prices['Đắk Nông']['change']},
                ],
                "pepper": {"price": f"{int(prices.get('Hồ tiêu', {}).get('price', 0)):,}", "change": prices.get('Hồ tiêu', {}).get('change', '0')},
                "exchange": {"usd_vnd": prices.get('USD/VND', {}).get('price', 'N/A')},
                "timestamp": int(time.time()),
                "date": datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S"),
                "unit": "VNĐ/kg"
            }
        else:
            print("Scrape thiếu dữ liệu - không đủ tỉnh, log prices để debug")
            raise Exception("Scrape thiếu dữ liệu - xem HTML/log để fix regex")

    except Exception as e:
        print("Lỗi scrape:", str(e))
        raise  # Không fallback – để crash và log lỗi, xem lý do thật sự

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
