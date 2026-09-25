import urllib.request
from bs4 import BeautifulSoup
import json
import ssl
import time

def scrape_iweb_services(domain):
    """
    Scrapes services from municipalities using the i-web CMS (e.g. Uster, Meilen, Küsnacht).
    They typically list their services on a dedicated A-Z or overview page.
    """
    url = f"https://{domain}/dienstleistungen"
    services = []
    
    # Create an unverified context if needed
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req, context=ctx).read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        
        # In i-web, lists of services are often found in lists (ul/li) under specific classes
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').lower()
            if '/dienstleistung' in href or '/onlinedienst' in href:
                title = link.get_text(strip=True)
                if len(title) > 3 and title not in services:
                    services.append(title)
                    
        return services
    except Exception as e:
        print(f"Failed to scrape {domain}: {e}")
        return []

def run_scraper(domains):
    all_data = {}
    for domain in domains:
        print(f"Scraping {domain}...")
        services = scrape_iweb_services(domain)
        all_data[domain] = services
        time.sleep(1) # Be polite
        
    with open("municipality_services.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print("Scraping completed and saved.")

if __name__ == '__main__':
    # A sample of Swiss municipalities
    target_municipalities = [
        "www.uster.ch",
        "www.meilen.ch",
        "www.kuesnacht.ch",
        "www.wetzikon.ch"
    ]
    run_scraper(target_municipalities)
