import time
import re
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify
from datetime import datetime, timezone, timedelta

# --- Cấu hình ---
CACHE_DURATION_SECONDS = 3 * 60 * 60  # Cache 3 giờ
SCRAPERAPI_KEY = "406d12726797254e25a327312ff5bf44"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'vi-VN,vi;q=0.9,en;q=0.8',
    'Connection': 'keep-alive',
}

# --- Flask ---
app = Flask(__name__)
application = app

# --- Cache ---
cached_data = {
    "data": None,
    "timestamp": 0
}

def get_coffee_prices():
    """
    Scrape dữ liệu từ giacaphe.com sử dụng ScraperAPI để tránh Cloudflare.
    """
    url = "https://giacaphe.com/gia-ca-phe-noi-dia/"
    vn_tz = timezone(timedelta(hours=7))
    params = {
        "api_key": SCRAPERAPI_KEY,
        "url": url
    }

    for attempt in range(2):
        try:
            time.sleep(2)
            print(f"Scrape attempt {attempt+1}...")
            response = requests.get("https://api.scraperapi.com", params=params, headers=HEADERS)
            
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}")

            soup = BeautifulSoup(response.text, 'lxml')
            full_text = soup.get_text()

            # Regex tìm giá theo tỉnh + thay đổi
            pattern_price = re.compile(
                r'(Đắk Lắk|Trung bình|Đắk Nông|Gia Lai|Lâm Đồng)\s*[:\-]?\s*(\d{3}(?:,\d{3})*)\s*(\([+-]?\d{1,3}(?:,\d{3})*\))?',
                re.IGNORECASE
            )
            matches = pattern_price.findall(full_text)

            pepper_match = re.search(r'Hồ tiêu\s*[:\-]?\s*(\d{3}(?:,\d{3})*)\s*(\([+-]?\d{1,3}(?:,\d{3})*\))?', full_text)
            exchange_match = re.search(r'Tỷ giá USD/VND\s*[:\-]?\s*(\d{2,3}(?:,\d{3})*)', full_text)

            prices = {}
            changes = {}

            for m in matches:
                province = m[0].strip()
                price = m[1].replace(',', '')
                change = m[2].strip('()') if m[2] else '0'
                prices[province] = f"{int(price):,}"
                changes[province] = change

            if len(prices) >= 4:
                print("✔ Scrape thành công (full)")
                return {
                    "source": "giacaphe.com (scrape full via ScraperAPI)",
                    "average": {"price": prices.get("Trung bình", "N/A"), "change": changes.get("Trung bình", "0")},
                    "prices": [
                        {"province": "Đắk Lắk", "price": prices.get("Đắk Lắk", "N/A"), "change": changes.get("Đắk Lắk", "0")},
                        {"province": "Lâm Đồng", "price": prices.get("Lâm Đồng", "N/A"), "change": changes.get("Lâm Đồng", "0")},
                        {"province": "Gia Lai", "price": prices.get("Gia Lai", "N/A"), "change": changes.get("Gia Lai", "0")},
                        {"province": "Đắk Nông", "price": prices.get("Đắk Nông", "N/A"), "change": changes.get("Đắk Nông", "0")},
                    ],
                    "pepper": {
                        "price": pepper_match.group(1).replace(',', '') if pepper_match else "N/A",
                        "change": pepper_match.group(2).strip('()') if pepper_match and pepper_match.group(2) else "0"
                    },
                    "exchange": {
                        "usd_vnd": exchange_match.group(1).replace(',', '') if exchange_match else "N/A"
                    },
                    "timestamp": int(time.time()),
                    "date": datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S"),
                    "unit": "VNĐ/kg (tỷ giá: VND/USD)"
                }

            print(f"Scrape thiếu dữ liệu ({len(prices)} items). Thử lại...")

        except Exception as e:
            print(f"Lỗi scrape attempt {attempt+1}: {e}")
            continue

    # Fallback
    print("⚠ Dùng fallback do scrape fail")
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
        "date": datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S"),
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
        print("→ Trả từ cache")
        return jsonify(cached_data["data"])

    fresh_data = get_coffee_prices()

    cached_data["data"] = fresh_data
    cached_data["timestamp"] = current_time

    print("→ Trả dữ liệu mới (fresh)")
    return jsonify(fresh_data)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
