import asyncio
import httpx
from bs4 import BeautifulSoup

async def fetch_bookswagon(query):
    print(f"Testing BooksWagon for: {query}")
    url = f"https://www.bookswagon.com/search-books/{query.replace(' ', '+')}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        print("BooksWagon Status:", response.status_code)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # The book lists are usually in div class 'list-view-books' or similar
            items = soup.select('.list-view-books, .col-sm-12 .card')
            if items:
                print(f"Found {len(items)} items on BooksWagon")
                for item in items[:1]:
                    title = item.select_one('.title, .booktitle')
                    price = item.select_one('.price, .sell')
                    print(f"Title: {title.text.strip() if title else 'N/A'}")
                    print(f"Price: {price.text.strip() if price else 'N/A'}")
            else:
                print("No items found using selector.")
        else:
            print("Failed to fetch.")

async def fetch_crossword(query):
    print(f"\nTesting Crossword for: {query}")
    url = f"https://www.crossword.in/search?q={query.replace(' ', '+')}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        print("Crossword Status:", response.status_code)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.select('.product-item')
            if items:
                print(f"Found {len(items)} items on Crossword")
                for item in items[:1]:
                    title = item.select_one('.product-item__title')
                    price = item.select_one('.price-item')
                    print(f"Title: {title.text.strip() if title else 'N/A'}")
                    print(f"Price: {price.text.strip() if price else 'N/A'}")
            else:
                print("No items found using selector.")
        else:
            print("Failed to fetch.")

async def main():
    await fetch_bookswagon("Dune Frank Herbert")
    await fetch_crossword("Dune Frank Herbert")

if __name__ == "__main__":
    asyncio.run(main())
