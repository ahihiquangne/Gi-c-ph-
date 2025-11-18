def get_coffee_prices():
    """
    Hàm lấy giá cà phê với bypass Cloudflare nâng cao.
    """
    url = "https://giacaphe.com/gia-ca-phe-noi-dia/"

    # Tạo scraper giống trình duyệt thật
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        }
    )

    headers = {
        "User-Agent": scraper.get_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://google.com/",
        "Upgrade-Insecure-Requests": "1",
        "DNT": "1"
    }

    try:
        response = scraper.get(url, headers=headers)

        # Debug nếu còn bị chặn
        if response.status_code == 403:
            print("❌ Bị chặn Cloudflare (403). HTML trả về:")
            print(response.text[:500])
            return None

        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'lxml')

        # Lấy toàn bộ CSS
        all_css_text = "".join(
            style.string for style in soup.find_all("style") if style.string
        )

        pattern = re.compile(r"::after\s*{\s*content:\s*'([^']+)'")
        values = pattern.findall(all_css_text)

        if len(values) < 4:
            print("❌ Không tìm đủ dữ liệu trong CSS. Giá trị tìm thấy:")
            print(values)
            return None

        data = {
            "source": "giacaphe.com",
            "prices": {
                "Đắk Lắk": values[0],
                "Lâm Đồng": values[1],
                "Gia Lai": values[2],
                "Đắk Nông": values[3],
            },
            "timestamp": int(time.time()),
            "date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "text": (
                "Giá cà phê nội địa \n"
                f"Đắk Lắk: {values[0]}\n"
                f"Lâm Đồng: {values[1]}\n"
                f"Gia Lai: {values[2]}\n"
                f"Đắk Nông: {values[3]}"
            ),
            "unit": "VNĐ/kg"
        }
        return data

    except Exception as e:
        print(f"Lỗi khi lấy dữ liệu: {e}")
        return None
