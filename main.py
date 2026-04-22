import spacy
from database import OfferDatabase
from scraper import get_jobs_olx
from scraper_pracuj import get_jobs_pracuj

def process_and_save_offers(offers, db, nlp):
    """Przetwarza opisy zebranych ofert modelem spacy i zapisuje do bazy."""
    for offer in offers:
        desc = offer.get("description")
        
        # Zabezpieczenie przed brakiem opisu – by otrzymać wektor zerowy
        if not desc or desc == "N/A":
            desc = ""
            
        # Przetwarzanie opisu modelem spacy
        doc = nlp(desc)
        vector = doc.vector # Uzyskanie wektora dokumentu (np.ndarray)
        
        # Opcjonalne wyswietlanie postepu
        title = offer.get('title', 'Brak tytułu')
        print(f" -> Zapisywanie do bazy: {title}")
        
        # Wstawienie do bazy
        db.insert_offer(offer, vector=vector)

def main(city="Krakow", query=""):
    print("Ładowanie modelu spacy (en_core_web_sm)...")
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        print("Nie znaleziono modelu 'en_core_web_sm'.")
        print("Uruchom w terminalu: python -m spacy download en_core_web_sm")
        return

    print(f"\nPobieranie ofert pracy... Zapytanie: '{query}', Lokacja: '{city}'")
    
    # --- 1. Pobieranie OLX ---
    print("\n[1/2] Uruchamianie scrapera OLX...")
    olx_offers = get_jobs_olx(city, query)
    print(f"Pobrano {len(olx_offers)} ofert z OLX.")

    # --- 2. Pobieranie Pracuj.pl ---
    print("\n[2/2] Uruchamianie scrapera Pracuj.pl...")
    pracuj_offers = get_jobs_pracuj(city, query)
    print(f"Pobrano {len(pracuj_offers)} ofert z Pracuj.pl.")

    # --- 3. Przetwarzanie wektorów i zapis do bazy ---
    print("\nRozpoczynanie przetwarzania i wrzucania wektorów do bazy SQLite (offers.db)...")
    with OfferDatabase() as db:
        if olx_offers:
            print("\nZapisywanie ofert OLX:")
            process_and_save_offers(olx_offers, db, nlp)
            
        if pracuj_offers:
            print("\nZapisywanie ofert Pracuj.pl:")
            process_and_save_offers(pracuj_offers, db, nlp)

    print("\nZakończono pobieranie i zapisywanie. Baza została zaktualizowana!")

if __name__ == "__main__":
    import sys
    
    # Przykładowe użycie: python main.py "Krakow" "Python"
    # Jeśli argumenty nie są podane, zostaną obsłużone domyślnie
    cmd_city = sys.argv[1] if len(sys.argv) > 1 else "Krakow"
    cmd_query = sys.argv[2] if len(sys.argv) > 2 else ""
    
    main(city=cmd_city, query=cmd_query)