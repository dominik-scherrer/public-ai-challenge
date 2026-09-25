import urllib.request
import re

def get_sitemap_urls(domain):
    try:
        req = urllib.request.Request(f"https://{domain}/sitemap.xml", headers={'User-Agent': 'Mozilla/5.0'})
        xml = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')
        urls = re.findall(r'<loc>(.*?)</loc>', xml)
        
        # filter for dienstleistung or onlinedienst
        services = []
        for u in urls:
            if 'dienst' in u.lower():
                services.append(u)
        return services
    except Exception as e:
        print(f"Error for {domain}: {e}")
        return []

if __name__ == '__main__':
    domains = ["www.uster.ch", "www.meilen.ch"]
    for d in domains:
        print(f"--- {d} ---")
        urls = get_sitemap_urls(d)
        for u in urls[:20]: # print first 20
            print(u)
        print(f"Total services found: {len(urls)}")
