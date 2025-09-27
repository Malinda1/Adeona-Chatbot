import asyncio
from backend.app.services.web_scraper import WebScraper

async def main():
    async with WebScraper() as scraper:
        # Test scraping a single page
        content = await scraper.scrape_page("/")
        if content:
            print(f"URL: {content.url}")
            print(f"Title: {content.title}")
            print(f"Content Preview: {content.content[:500]}...\n")
        else:
            print("Failed to scrape the page.")

        # Test scraping all pages
        all_content = await scraper.scrape_all_pages()
        print(f"Total pages scraped: {len(all_content)}")
        for page in all_content:
            print(f"- {page.url} ({page.page_type})")

        # Test chunking
        if content:
            chunks = scraper.chunk_content(content, chunk_size=200, overlap=50)
            print(f"Number of chunks: {len(chunks)}")
            for i, chunk in enumerate(chunks[:2]):  # show first 2 chunks
                print(f"Chunk {i}: {chunk['text'][:100]}...")

if __name__ == "__main__":
    asyncio.run(main())
