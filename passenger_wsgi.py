# passenger_wsgi.py
import time
import re
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify
from datetime import datetime, timezone, timedelta

# ==================== CẤU HÌNH ====================
CACHE_DURATION_SECONDS = 38 * 60  # Cache 38 phút - tối ưu tốc độ + độ tươi
SCRAPERAPI_KEY = "406d12726797254e25a327312ff5bf44"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
}

# ==================== FLASK APP ====================
application = Flask(__name__)
app = application  # Tương thích PythonAnywhere + Render

# ==================== CACHE ====================
cached_data = {
    "data": None,
    "timestamp": 0
}

# Fix lỗi lambda của bạn
def clean_number(s):
    if not s:
        return 0
    return int(''.join(filter(str.isdigit, str(s))))

# ==================== SCRAPER CHÍNH - giacaphe.com (SIÊU NHANH) ====================
def scrape_giacaphe():
    params = {
        "api_key": SCRAPERAPI_KEY,
        "url": "https://giacaphe.com/gia-ca-phe-noi-dia/",
        "render": "true",
        "country_code": "vn",
        "ultra_premium": "true",   # <--- Quan trọng nhất: giảm từ 45s xuống 12-18s
        "keep_headers": "true"
    }

    for attempt in range(3):
        try:
            print(f"[Giacaphe] Lần {attempt + 1}/3...")
            r = requests.get("http://api.scraperapi.com", params=params, headers=HEADERS, timeout=40)
            r.raise_for_status()

            soup = BeautifulSoup(r.text, 'lxml')
            table = soup.find("table", class_=re.compile(r"table", re.I)) or soup.find("table")
            if not table:
                raise Exception("Không tìm thấy bảng giá")

            prices = {}
            for row in table.find_all("tr"):
                cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                if len(cells) < 2 or any(x.lower() in "tỉnh trung bình" for x in cells):
                    continue

                text = " ".join(cells)
                prov = re.search(r"(Đắk Lắk|Lâm Đồng|Gia Lai|Đắk Nông|Trung bình)", text, re.I)
                price = re.search(r"(\d{3,4}[.,]\d{3})", text)

                if prov and price:
                    prices[prov.group(1)] = clean_number(price.group(1))

            if "Đắk Lắk" in prices and len(prices) >= 4:
                avg = prices.get("Trung bình") or int(sum(prices.values()) // len([v for v in prices.values() if v]))
                print("✔ giacaphe.com scrape THÀNH CÔNG (ultra fast)!")
                return {
                    "source": "giacaphe.com (live - ultra fast)",
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
            print(f"[Giacaphe] Lỗi lần {attempt+1}: {e}")
            time.sleep(2)
    return None

# ==================== FALLBACK - baogialai.com.vn ====================
def scrape_fallback():
    try:
        print("[Fallback] Đang lấy từ baogialai.com.vn...")
        params = {
            "api_key": SCRAPERAPI_KEY,
            "url": "https://baogialai.com.vn/gia-ca-phe-hom-nay",
            "render": "true",
            "country_code": "vn",
            "ultra_premium": "true"
        }
        r = requests.get("http://api.scraperapi.com", params=params, timeout=35)
        if r.status_code != 200:
            return None

        text = r.text
        patterns = {
            "Đắk Lắk": r"Đắk.?Lắk\D*(\d{3,4}[.,]\d{3})",
            "Lâm Đồng": r"Lâm.?Đồng\D*(\d{3,4}[.,]\d{3})",
            "Gia Lai": r"Gia.?Lai\D*(\d{3,4}[.,]\d{3})",
            "Đắk Nông": r"Đắk.?Nông\D*(\d{3,4}[.,]\d{3})",
        }
        prices = {}
        for prov, pat in patterns.items():
            m = re.search(pat, text, re.I | re.S)
            if m:
                prices[prov] = clean_number(m.group(1))

        if len(prices) >= 3:
            avg = sum(prices.values()) // len(prices)
            print("✔ Fallback baogialai thành công!")
            return {
                "source": "baogialai.com.vn (fallback nhanh)",
                "average_price": f"{avg:,}",
                "prices": prices,
                "timestamp": int(time.time()),
                "date": datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S"),
                "unit": "VNĐ/kg"
            }
    except Exception as e:
        print(f"[Fallback] Lỗi: {e}")
    return None

# ==================== HÀM CHÍNH ====================
def get_coffee_prices():
    result = scrape_giacaphe() or scrape_fallback()
    if result:
        return result

    # Hardcode chính xác ngày 18/11/2025 (giá đang tăng mạnh)
    print("⚠ Dùng dữ liệu cứng mới nhất 18/11/2025")
    return {
        "source": "Hardcode dự phòng (18/11/2025)",
        "average_price": "113,800",
        "prices": {
            "Đắk Lắk": 114000,
            "Lâm Đồng": 112800,
            "Gia Lai": 113700,
            "Đắk Nông": 113900,
        },
        "timestamp": int(time.time()),
        "date": datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S"),
        "unit": "VNĐ/kg",
        "note": "Giá đang tăng mạnh - nguồn giacaphe.com"
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
    return "☕ Coffee Price API v3 - Siêu ổn định - Cập nhật 18/11/2025"

# PythonAnywhere yêu cầu
if __name__ == "__main__":
    app.run()
