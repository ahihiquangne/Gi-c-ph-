import time
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify
from datetime import datetime, timezone, timedelta

# --- Cấu hình ---
CACHE_DURATION_SECONDS = 45 * 60  # Cache 45 phút thôi (giá cà phê biến động mạnh)
SCRAPERAPI_KEY = "406d12726797254e25a327312ff5bf44"  # Bạn giữ nguyên hoặc chuyển sang env sau
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
}

app = Flask(__name__)
application = app

# Cache
cached_data = {
    "data": None,
    "timestamp": 0
}

def clean_number(text):
    return text.replace(',', '').replace('.', '').strip()

def scrape_giacaphe():
    url = "https://giacaphe.com/gia-ca-phe-noi-dia/"
    params = {
        "api_key": SCRAPERAPI_KEY,
        "url": url,
        "render": "true",           # Bắt buộc bật JS rendering
        "country_code": "vn",       # Giả lập IP Việt Nam → ít bị block hơn
        "premium": "true",          # Dùng proxy residential tốt hơn
        "keep_headers": "true"
    }

    for attempt in range(3):
        try:
            print(f"[Giacaphe] Scrape attempt {attempt + 1}...")
            response = requests.get("http://api.scraperapi.com", params=params, headers=HEADERS, timeout=60)
            
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}")

            soup = BeautifulSoup(response.text, 'lxml')

            # Cách mới: lấy trực tiếp từ bảng chính
            table = soup.find("table", class_=re.compile(r"table.*coffee", re.I))
            if not table:
                # Fallback tìm bất kỳ table nào có từ "Đắk Lắk"
                tables = soup.find_all("table")
                for t in tables:
                    if "Đắk Lắk" in t.get_text():
                        table = t
                        break
            if not table:
                raise Exception("Không tìm thấy bảng giá")

            prices = {}
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                text = " ".join([c.get_text(strip=True) for c in cells])
                if not text or "tỉnh" in text.lower():
                    continue

                # Match tỉnh + giá
                province_match = re.search(r"(Đắk Lắk|Lâm Đồng|Gia Lai|Đắk Nông|Trung bình)", text, re.I)
                price_match = re.search(r"(\d{3,4}[.,]\d{3})", text.replace(',', ''))
                change_match = re.search(r"([+-]?\d{1,4}[.,]?\d*)", text.replace(price_match.group(1), '') if price_match else text)

                if province_match and price_match:
                    province = province_match.group(1).strip()
                    price = clean_number(price_match.group(1))
                    change = change_match.group(1).replace('+', '').strip() if change_match else "0"
                    prices[province] = {"price": price, "change": change}

            pepper = re.search(r"Hồ tiêu.*?(\d{2,3}[.,]\d{3})", response.text, re.I)
            usd = re.search(r"USD/VND.*?(\d{2,3}[.,]\d{3})", response.text, re.I)

            if "Đắk Lắk" in prices and len(prices) >= 4:
                print("✔ [Giacaphe] Scrape thành công!")
                return {
                    "source": "giacaphe.com (live via ScraperAPI + JS render)",
                    "average": {
                        "price": f"{int(prices.get('Trung bình', {}).get('price', 0)):,}",
                        "change": prices.get('Trung bình', {}).get('change', "0")
                    },
                    "prices": [
                        {"province": "Đắk Lắk", "price": f"{int(prices['Đắk Lắk']['price']):,}", "change": prices['Đắk Lắk']['change']},
                        {"province": "Lâm Đồng", "price": f"{int(prices.get('Lâm Đồng', {}).get('price', 0)):,}", "change": prices.get('Lâm Đồng', {}).get('change', "0")},
                        {"province": "Gia Lai", "price": f"{int(prices.get('Gia Lai', {}).get('price', 0)):,}", "change": prices.get('Gia Lai', {}).get('change', "0")},
                        {"province": "Đắk Nông", "price": f"{int(prices.get('Đắk Nông', {}).get('price', 0)):,}", "change": prices.get('Đắk Nông', {}).get('change', "0")},
                    ],
                    "pepper": {
                        "price": pepper.group(1).replace(',', '') if pepper else "N/A",
                        "change": "0"
                    },
                    "exchange": {"usd_vnd": usd.group(1).replace(',', '') if usd else "N/A"},
                    "timestamp": int(time.time()),
                    "date": datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S"),
                    "unit": "VNĐ/kg"
                }
        except Exception as e:
            print(f"[Giacaphe] Lỗi attempt {attempt+1}: {e}")
            time.sleep(3)

    return None

def scrape_fallback_baogialai():
    try:
        print("[Fallback] Đang lấy từ baogialai.com.vn...")
        params = {
            "api_key": SCRAPERAPI_KEY,
            "url": "https://baogialai.com.vn/gia-ca-phe-hom-nay",
            "render": "true",
            "country_code": "vn"
        }
        response = requests.get("http://api.scraperapi.com", params=params, timeout=60)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'lxml')
        text = soup.get_text()
        prices = {}
        for province, pattern in [
            ("Đắk Lắk", r"Đắk.?Lắk.*?(\d{3,4}[.,]\d{3})"),
            ("Lâm Đồng", r"Lâm.?Đồng.*?(\d{3,4}[.,]\d{3})"),
            ("Gia Lai", r"Gia.?Lai.*?(\d{3,4}[.,]\d{3})"),
            ("Đắk Nông", r"Đắk.?Nông.*?(\d{3,4}[.,]\d{3})"),
        ]:
            m = re.search(pattern, text, re.I | re.S)
            if m:
                prices[province] = clean_number(m.group(1))

        if len(prices) >= 3:
            avg = str(int(sum(int(v) for v in prices.values() if v.isdigit()) / len(prices)))
            print("✔ [Fallback] Thành công từ baogialai!")
            return {
                "source": "baogialai.com.vn (fallback tự động)",
                "average": {"price": f"{int(avg):,}", "change": "?"},
                "prices": [
                    {"province": k, "price": f"{int(v):,}" if v.isdigit() else "N/A", "change": "?"}
                    for k, v in prices.items()
                ],
                "pepper": {"price": "N/A", "change": "0"},
                "exchange": {"usd_vnd": "N/A"},
                "timestamp": int(time.time()),
                "date": datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S"),
                "unit": "VNĐ/kg",
                "note": "Nguồn phụ khi giacaphe.com lỗi"
            }
    except:
        pass
    return None

def get_coffee_prices():
    result = scrape_giacaphe()
    if result:
        return result
    
    print("⚠ Chuyển sang fallback...")
    result = scrape_fallback_baogialai()
    if result:
        return result

    # Cuối cùng mới dùng hardcode (chỉ khi cả 2 nguồn die)
    print("⚠ Dùng dữ liệu cứng (cuối cùng)")
    return {
        "source": "Hardcode fallback (18/11/2025)",
        "average": {"price": "116,800", "change": "+1,200"},
        "prices": [
            {"province": "Đắk Lắk", "price": "117,000", "change": "+1,300"},
            {"province": "Lâm Đồng", "price": "115,200", "change": "+1,100"},
            {"province": "Gia Lai", "price": "116,500", "change": "+1,200"},
            {"province": "Đắk Nông", "price": "116,800", "change": "+1,200"}
        ],
        "pepper": {"price": "148,000", "change": "+1,000"},
        "exchange": {"usd_vnd": "26,150"},
        "timestamp": int(time.time()),
        "date": datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S"),
        "unit": "VNĐ/kg",
        "note": "Dữ liệu dự phòng"
    }

# ==================== ROUTES ====================
@app.route('/')
def home():
    return jsonify({"message": "Coffee Price API v2 - Cập nhật 18/11/2025"})

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/api/coffee-prices')
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
    app.run(host='0.0.0.0', port=5000, debug=False)
