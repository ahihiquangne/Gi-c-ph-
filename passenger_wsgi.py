def get_coffee_prices():
    """
    Lấy giá cà phê thông qua ScraperAPI để bypass Cloudflare.
    """
    import requests
    from bs4 import BeautifulSoup
    import re
    import time

    SCRAPER_API_KEY = "406d12726797254e25a327312ff5bf44"
    target_url = "https://giacaphe.com/gia-ca-phe-noi-dia/"

    payload = {
        "api_key": SCRAPER_API_KEY,
        "url": target_url,
        "render": "html",
        "device_type": "desktop",
        "session_number": 1
    }

    try:
        # Request qua ScraperAPI
        response = requests.get("https://api.scraperapi.com/", params=payload)
        response.raise_for_status()

        # Parse HTML thực
        soup = BeautifulSoup(response.text, "lxml")

        # Gom toàn bộ CSS trong <style>
        all_css_text = "".join(style.get_text() for style in soup.find_all("style"))

        # Regex để lấy content: 'xxxxx'
        pattern = re.compile(r"::after\s*{\s*content:\s*'([^']+)';?\s*}")
        values = pattern.findall(all_css_text)

        if len(values) < 4:
            print("⚠ Không đủ dữ liệu trong CSS. values =", values)
            return None

        data = {
            "source": "giacaphe.com (ScraperAPI)",
            "prices": {
                "Đắk Lắk": values[0],
                "Lâm Đồng": values[1],
                "Gia Lai": values[2],
                "Đắk Nông": values[3],
            },
            "timestamp": int(time.time()),
            "date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "text": (
                "Giá cà phê nội địa\n"
                f"Đắk Lắk: {values[0]}\n"
                f"Lâm Đồng: {values[1]}\n"
                f"Gia Lai: {values[2]}\n"
                f"Đắk Nông: {values[3]}"
            ),
            "unit": "VNĐ/kg"
        }
        return data

    except Exception as e:
        print(f"❌ Lỗi khi dùng ScraperAPI: {e}")
        return None
