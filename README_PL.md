# Web Nanny

Web Nanny to lekki monitor dla dziecka działający w przeglądarce z transmisją audio przez WebRTC i detekcją płaczu.

## Funkcje

- Przesyłanie dźwięku w czasie rzeczywistym przez WebRTC
- Jeden nadajnik i jeden odbiornik
- Detekcja płaczu po stronie odbiornika
- Wsparcie lokalnego HTTPS/WSS
- Obsługa Dockera dla Raspberry Pi / NAS

## Uruchomienie lokalne

### Wymagania

- Python 3.11+
- Docker (opcjonalnie, zalecane na Raspberry Pi)
- Przeglądarka z obsługą WebRTC

### Uruchomienie z Pythonem

1. Utwórz virtualenv:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Wygeneruj certyfikaty:
   ```bash
   openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes \
     -subj "/C=PL/ST=Warsaw/L=Warsaw/O=WebNanny/CN=localhost"
   ```

3. Uruchom serwer:
   ```bash
   python main.py
   ```

4. Otwórz w przeglądarce:
   - `https://<host>:8001/sender`
   - `https://<host>:8001/listener`

### Uruchomienie z Dockerem

1. Zbuduj obraz:
   ```bash
   docker build -t web_nanny .
   ```

2. Uruchom kontener:
   ```bash
   docker-compose up -d
   ```

3. Otwórz w przeglądarce:
   - `https://<raspi-ip>:8001`

## Przepływ użytkowania

1. Przejdź do strony głównej pod adresem `https://<host>:8001`.
2. Wybierz preferowany język (polski lub angielski).
3. Wybierz swoją rolę: Nadajnik (do nadawania dźwięku) lub Odbiornik (do odbioru i monitorowania dźwięku z detekcją płaczu).
4. Postępuj zgodnie z instrukcjami na ekranie, aby rozpocząć/zatrzymać transmisję dźwięku.

## Uwagi

- Nie dodawaj do repozytorium `cert.pem`, `key.pem` ani innych plików z kluczami.
- Projekt jest przeznaczony do zaufanej sieci lokalnej.
- Do produkcji użyj ważnych certyfikatów TLS i dodaj uwierzytelnianie.
