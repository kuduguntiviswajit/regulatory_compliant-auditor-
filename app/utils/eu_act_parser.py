import re
import json


def load_pdf_text(file_path: str) -> str:
    from langchain_community.document_loaders import PyPDFLoader

    loader = PyPDFLoader(file_path)
    documents = loader.load()

    full_text = "\n".join([doc.page_content for doc in documents])
    return full_text


def extract_articles(text: str):
    """
    Extract real EU AI Act article sections only.
    """
    pattern = r"(?m)^Article\s+\d+\s*$.*?(?=^Article\s+\d+\s*$|\Z)"
    articles = re.findall(pattern, text, re.DOTALL)
    return articles


if __name__ == "__main__":
    file_path = "data/raw/eu_ai_act_2024.pdf"

    print("Loading EU AI Act PDF...")
    text = load_pdf_text(file_path)

    print("Extracting Articles...")
    raw_articles = extract_articles(text)

    structured_articles = {}
    
    for article in raw_articles:
        lines = article.strip().split("\n")

        # First line → "Article X"
        header = lines[0].strip()
        article_number = header.replace("Article", "").strip()

        # Second line → title
        title = lines[1].replace("`" , "").strip() if len(lines) > 1 else ""

        # Remaining lines → full content
        content = "\n".join(lines[2:]).strip()

        # Avoid duplicates
        if article_number not in structured_articles:
            structured_articles[article_number] = {
                "article_number": article_number,
                "title": title,
                "content": content
            }

    print("\nTotal Unique Articles Found:", len(structured_articles))

    # Convert dict → list
    articles_list = list(structured_articles.values())

    # Save to JSON
    output_path = "data/eu_ai_act_articles.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(articles_list, f, indent=4, ensure_ascii=False)

    print(f"\nStructured JSON saved to: {output_path}")

    # Preview first article
    print("\nPreview of First Article:\n")
    print(json.dumps(articles_list[0], indent=4)[:1000])

