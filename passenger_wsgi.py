# passenger_wsgi.py
import time
import re
import requests
from flask import Flask, jsonify
from datetime import datetime, timezone, timedelta

# ==================== CẤU HÌNH ====================
CACHE_DURATION_SECONDS = 40 * 60  # Cache 40 phút (giá cà phê giờ thay đổi rất nhanh)
SCRAPERAPI_KEY = "406d12726797254e25a327312ff5bf44"  # Giữ nguyên hoặc chuyển sang env sau

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
}

# ==================== FLASK APP ====================
application = Flask(__name__)
app = application  # Tương thích cả hai tên

# ==================== CACHE ====================
cached_data = {
    "data": None,
    "timestamp": 0
}

def clean_number = lambda s: int(''.join(filter(str.isdigit, str(s)))) if s else 0

# ==================== SCRAPER CHÍNH (giacaphe.com) ====================
def scrape_giacaphe():
    params = {
        "api_key": SCRAPERAPI_KEY,
        "url": "https://giacaphe.com/gia-ca-phe-noi-dia/",
        "render": "true",         # Bắt buộc render JavaScript
        "country_code": "vn",     # IP Việt Nam → ít bị chặn hơn
        "premium": "true",
        "keep_headers": "true",
        "timeout": "60"
    }

    for attempt in range(3):
        try:
            print(f"[Giacaphe] Attempt {attempt + 1}/3...")
            r = requests.get("http://api.scraperapi.com", params=params, headers=HEADERS, timeout=90)
            if r.status_code != 200:
                raise Exception(f"HTTP {r.status_code}")

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, 'lxml')

            # Tìm bảng giá chính xác nhất
            table = soup.find("table", {"class": re.compile("table", re.I)}) or soup.find("table")
            if not table:
                raise Exception("Không tìm thấy bảng")

            prices = {}
            for row in table.find_all("tr"):
                cells = row.find_all(["td", "th"])
                text = " ".join(c.get_text(strip=True) for c in cells)
                if not text or "tỉnh" in text.lower():
                    continue

                province_match = re.search(r"(Đắk Lắk|Lâm Đồng|Gia Lai|Đắk Nông|Trung bình)", text, re.I)
                price_match = re.search(r"(\d{3,4}[.,]\d{3})", text.replace(".", "").replace(",", ""))

                if province_match and price_match:
                    province = province_match.group(1)
                    price = clean_number(price_match.group(1))
                    prices[province] = price

            if "Đắk Lắk" in prices and len(prices) >= 4:
                print("✔ Scrape giacaphe.com thành công!")
                avg = prices.get("Trung bình", int(sum(prices.values()) / len(prices)))
                return {
                    "source": "giacaphe.com (live)",
                    "average_price": f"{avg:,}",
                    "prices": {
                        "Đắk Lắk": prices.get("Đắk Lắk", 0),
                        "Lâm Đồng": prices.get("Lâm Đồng", 0),
                        "Gia Lai": prices.get("Gia Lai", 0),
                        "Đắk Nông": prices.get("Đắk Nông", 0),
                    },
                    "timestamp": int(time.time()),
                    "date": datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S"),
                    "unit": "VNĐ/kg"
                }
        except Exception as e:
            print(f"[Giacaphe] Lỗi attempt {attempt+1}: {e}")
            time.sleep(3)
    return None

# ==================== FALLBACK (baogialai.com.vn) ====================
def scrape_fallback():
    try:
        print("[Fallback] Lấy từ baogialai.com.vn...")
        params = {
            "api_key": SCRAPERAPI_KEY,
            "url": "https://baogialai.com.vn/gia-ca-phe-hom-nay",
            "render": "true",
            "country_code": "vn"
        }
        r = requests.get("http://api.scraperapi.com", params=params, timeout=60)
        if r.status_code != 200:
            return None

        text = r.text
        mapping = {
            "Đắk Lắk": r"Đắk.?Lắk\D*(\d{3,4}[.,]\d{3})",
            "Lâm Đồng": r"Lâm.?Đồng\D*(\d{3,4}[.,]\d{3})",
            "Gia Lai": r"Gia.?Lai\D*(\d{3,4}[.,]\d{3})",
            "Đắk Nông": r"Đắk.?Nông\D*(\d{3,4}[.,]\d{3})",
        }
        prices = {}
        for province, pattern in mapping.items():
            m = re.search(pattern, text, re.I | re.S)
            if m:
                prices[province] = clean_number(m.group(1))

        if len(prices) >= 3:
            avg = int(sum(prices.values()) / len(prices))
            print("✔ Fallback baogialai thành công!")
            return {
                "source": "baogialai.com.vn (fallback)",
                "average_price": f"{avg:,}",
                "prices": prices,
                "timestamp": int(time.time()),
                "date": datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S"),
                "unit": "VNĐ/kg",
                "note": "Nguồn phụ khi giacaphe.com lỗi"
            }
    except Exception as e:
        print(f"[Fallback] Lỗi: {e}")
    return None

# ==================== LẤY DỮ LIỆU CHÍNH ===
def get_coffee_prices():
    data = scrape_giacaphe() or scrape_fallback()

    if data:
        return data

    # Hardcode cuối cùng (18/11/2025)
    print("⚠ Dùng dữ liệu cứng")
    return {
        "source": "Hardcode fallback (18/11/2025)",
        "average_price": "116,800",
        "prices": {
            "Đắk Lắk": 117000,
            "Lâm Đồng": 115200,
            "Gia Lai": 116500,
            "Đắk Nông": 116800,
        },
        "timestamp": int(time.time()),
        "date": datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S"),
        "unit": "VNĐ/kg"
    }

# ==================== ROUTES ====================
@app.route('/api/coffee-prices')
def api_v1():
    global cached_data
    now = time.time()

    if cached_data["data"] and (now - cached_data["timestamp"] < CACHE_DURATION_SECONDS):
        return jsonify(cached_data["data"])

    fresh = get_coffee_prices()
    cached_data["data"] = fresh
    cached_data["timestamp"] = now
    return jsonify(fresh)

@app.route('/api/v2/coffee-prices')
def api_v2():
    global cached_data
    now = time.time()

    if not (cached_data["data"] and (now - cached_data["timestamp"] < CACHE_DURATION_SECONDS)):
        fresh = get_coffee_prices()
        cached_data["data"] = fresh
        cached_data["timestamp"] = now

    data = cached_data["data"]
    mapping = [
        {"provinceId": 1, "provinceName": "Đắk Lắk", "price": data["prices"]["Đắk Lắk"]},
        {"provinceId": 2, "provinceName": "Lâm Đồng", "price": data["prices"]["Lâm Đồng"]},
        {"provinceId": 3, "provinceName": "Gia Lai", "price": data["prices"]["Gia Lai"]},
        {"provinceId": 4, "provinceName": "Đắk Nông", "price": data["prices"]["Đắk Nông"]},
    ]

    return jsonify({
        "source": data["source"],
        "average_price": data["average_price"],
        "timestamp": data["timestamp"],
        "date": data["date"],
        "unit": data["unit"],
        "prices": mapping
    })

@app.route('/')
def home():
    return "Coffee Price API đang chạy ổn định – /api/coffee-prices hoặc /api/v2/coffee-prices"

# Tương thích PythonAnywhere
if __name__ == "__main__":
    app.run()
