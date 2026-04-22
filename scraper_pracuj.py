from curl_cffi import requests
from bs4 import BeautifulSoup

def build_pracuj_url(city, query, category="praca", filters=None):
    # Pracuj.pl URL structure: https://www.pracuj.pl/praca/{query};kw/{city};wp
    city = city.lower().replace(" ", "-") if city else ""
    query = query.lower().replace(" ", "-") if query else ""
    
    base_url = "https://www.pracuj.pl/"
    url = f"{base_url}{category}"
    
    if query:
        url += f"/{query};kw"
    if city:
        url += f"/{city};wp"
        
    if filters:
        params = []
        for key, value in filters.items():
            if isinstance(value, list):
                for v in value:
                     params.append(f"{key}={v}")
            else:
                 params.append(f"{key}={value}")
        
        if params:
            url += "?" + "&".join(params)
            
    return url

def fetch_offers(url):
    # Added some common headers to bypass simple bot-protections
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "pl,en-US;q=0.7,en;q=0.3"
    }
    try:
        response = requests.get(url, headers=headers, impersonate="chrome")
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        offers = []
        
        # Pracuj.pl listing grid. Structure varies, common data-tests are used.
        listing_grid = soup.find('div', {'data-test': 'section-offers'})
        
        if not listing_grid:
            # Fallback or empty, often wrapped in main container
            listing_grid = soup.find('div', class_=lambda c: c and 'listing' in c.lower())
            
        if not listing_grid:
            print("Nie znaleziono kontenera z ofertami. Pracuj.pl może wymagać ominięcia Cloudflare.")
            return []
            
        # Using data-test "default-offer" which is commonly used by pracuj.pl
        cards = listing_grid.find_all('div', {'data-test': 'default-offer'})
        
        for card in cards:
            try:
                title_tag = card.find('h2')
                if not title_tag: 
                     continue
                title = title_tag.text.strip()
                
                link_tag = card.find('a', href=True)
                if not link_tag: continue
                link = link_tag['href']
                if not link.startswith('http'):
                    link = "https://www.pracuj.pl" + link
                
                details = {
                    "price": None,
                    "location": None,
                    "contract": None,
                    "work_load": None
                }
                
                # Fetch details based on text keywords since class names are often dynamic
                for div in card.find_all(['li', 'p']):
                    text = div.get_text(separator=" ", strip=True)
                    if not text: continue
                    
                    if "PLN" in text or "zł" in text:
                        details["price"] = text
                    elif any(x in text.lower() for x in ["umowa", "b2b", "kontrakt", "samozatrudnienie"]):
                        details["contract"] = text
                    elif "etat" in text.lower() or "praca" in text.lower():
                        details["work_load"] = text
                
                # specific fetching for location which usually is placed in h4
                location_tag = card.find('h4')
                if location_tag:
                     details["location"] = location_tag.text.strip()
                else:
                    # fallback
                    for h5 in card.find_all('h5'):
                         if h5.text.strip():
                             details["location"] = h5.text.strip()
                             break
                
                price = details["price"] if details["price"] else "N/A"
                location = details["location"] if details["location"] else "N/A"
                contract = details["contract"] if details["contract"] else "N/A"
                work_load = details["work_load"] if details["work_load"] else "N/A"
                
                # ID is often the last part of the url
                offer_id = link.split('-')[-1] if '-' in link else link
                
                offers.append({
                    'id': offer_id,
                    'title': title,
                    'price': price,
                    'location': location,
                    'contract': contract,
                    'work_load': work_load,
                    'description': fetch_offer(link),
                    'url': link
                })
            except Exception as e:
                print(f"Error parsing card: {e}")
                continue
                
        return offers

    except Exception as e:
        print(f"Error fetching offers: {e}")
        return []

def fetch_offer(url):
    if url == None: return None
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, impersonate="chrome")
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for the section with daily tasks
        responsibilities = soup.find('div', {'data-test': 'section-responsibilities'})
        if responsibilities:
             return responsibilities.text.strip()
             
        # Fallback to older pracuj layout
        for h2 in soup.find_all('h2'):
            h2_text = h2.text.strip().lower()
            if "twój zakres obowiązków" in h2_text or "opis stanowiska" in h2_text:
                return h2.parent.text.strip()
                
        return "N/A"
    except Exception as e:
        print(f"Error fetching offer details: {e}")
        return "N/A"


def get_jobs_pracuj(city, query):
    url = build_pracuj_url(city, query)
    return fetch_offers(url)

