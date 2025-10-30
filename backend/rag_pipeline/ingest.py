# Step 1: Load and classify HTML files
from pathlib import Path
from bs4 import BeautifulSoup

def find_all_html_files(root_dir):
    return list(Path(root_dir).rglob("*.html"))


def is_content_page(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")

        # Extract visible text
        p_tags = soup.find_all("p")
        div_tags = soup.find_all("div")

        # Long paragraphs or divs with actual text
        long_ps = [p.get_text(strip=True) for p in p_tags if len(p.get_text(strip=True)) > 100]
        long_divs = [d.get_text(strip=True) for d in div_tags if len(d.get_text(strip=True)) > 200]

        # Get title
        title = soup.title.string.lower() if soup.title else ""

        # Skip common non-content pages
        skip_titles = ["index", "contents", "overview", "summary", "toc", "table of contents"]

        # Accept if meaningful content is found and title is not generic
        if (len(long_ps) >= 1 or len(long_divs) >= 1) and not any(t in title for t in skip_titles):
            return True
        return False

    except Exception as e:
        print(f"❌ Failed to parse {filepath}: {e}")
        return False


def extract_content(filepath):
    soup = BeautifulSoup(open(filepath, "r", encoding="utf-8"), "html.parser")
    title = soup.title.string if soup.title else "No title"
    body = soup.get_text(separator=" ", strip=True)
    return {"filepath": str(filepath), "title": title, "content": body}
