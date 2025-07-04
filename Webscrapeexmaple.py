from flask import Flask, jsonify, request, abort
import requests
from bs4 import BeautifulSoup

import os

app = Flask(__name__)

BASE_URL = "http://books.toscrape.com/catalogue/page-{}.html"

books = []

def scrape_books(max_pages=10):
    book_id = 1
    all_books = []
    for page in range(1, max_pages + 1):
        url = BASE_URL.format(page)
        res = requests.get(url)
        if res.status_code != 200:
            break
        soup = BeautifulSoup(res.text, "html.parser")
        articles = soup.select("article.product_pod")
        for book in articles:
            title = book.h3.a["title"]
            price = book.select_one("p.price_color").text.strip()
            rating = book.p["class"][1]  
            relative_url = book.h3.a["href"]
            full_url = "http://books.toscrape.com/catalogue/" + relative_url
            availability = book.select_one("p.instock.availability").text.strip()


            detail_res = requests.get(full_url)
            if detail_res.status_code != 200:
                continue
            detail_soup = BeautifulSoup(detail_res.text, "html.parser")

            # Description
            description_tag = detail_soup.select_one("#product_description + p")
            description = description_tag.text.strip() if description_tag else "No description available"

            # Image
            img_tag = detail_soup.select_one("div.item.active img")
            image_url = (
                "http://books.toscrape.com/" + img_tag["src"].replace("../", "")
                if img_tag and img_tag.get("src")
                else None
            )

            all_books.append({
                "id": book_id,
                "title": title,
                "price": price,
                "rating": rating,
                "url": full_url,
                "availability": availability,
                "description": description,
                "image_url": image_url
            })
            book_id += 1
    return all_books

books_loaded = False

@app.before_request
def load_books():
    global books_loaded, books
    if not books_loaded:
        print("Scraping books from website...")
        books = scrape_books(max_pages=10)
        print(f"Scraped {len(books)} books.")
        books_loaded = True


# API: Get all books, with optional pagination
@app.route("/books", methods=["GET"])
def get_books():
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
    except ValueError:
        return jsonify({"error": "Invalid pagination parameters"}), 400

    start = (page - 1) * per_page
    end = start + per_page
    data = books[start:end]
    return jsonify({
        "page": page,
        "per_page": per_page,
        "total_books": len(books),
        "books": data
    })

# API: Search books by title keyword (case insensitive)
@app.route("/books/search", methods=["GET"])
def search_books():
    query = request.args.get("title", "").strip()
    if not query:
        return jsonify({"error": "Query parameter 'title' is required"}), 400

    filtered = [b for b in books if query.lower() in b["title"].lower()]
    return jsonify({
        "query": query,
        "total_results": len(filtered),
        "books": filtered
    })

# API: Get book detail by ID
@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    book = next((b for b in books if b["id"] == book_id), None)
    if not book:
        abort(404, description="Book not found")
    return jsonify(book)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

