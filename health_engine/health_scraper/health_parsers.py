from bs4 import BeautifulSoup


def parse_yjc_health(html):
    soup = BeautifulSoup(html, "html.parser")

    # title
    title_tag = soup.select_one("span.title-news")
    title = title_tag.get_text(strip=True) if title_tag else None

    # content
    content_div = soup.select_one("div.row.baznashr-body")

    paragraphs = []
    if content_div:
        for p in content_div.find_all("p"):
            text = p.get_text(strip=True)
            if text:
                paragraphs.append(text)

    clean_text = "\n".join(paragraphs)

    return {
        "title": title,
        "clean_text": clean_text,
    }