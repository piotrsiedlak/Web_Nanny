# Web Nanny

Web Nanny to lekki monitor dla dziecka działający w przeglądarce z transmisją audio przez WebRTC i detekcją płaczu.

## Funkcje

- Przesyłanie dźwięku w czasie rzeczywistym przez WebRTC
- Jeden nadajnik i jeden odbiornik
- Detekcja płaczu po stronie odbiornika
- Wsparcie lokalnego HTTPS/WSS
- Obsługa Dockera dla Raspberry Pi / NAS

## Nowości (ostatnie zmiany)

- Automatyczne generowanie certyfikatów TLS przy starcie, gdy `TLS_ENABLED=true` i certyfikaty nie istnieją (nie jest wymagane montowanie certyfikatów z hosta w Docker). (commit: Add automatic TLS certificate generation and simplify Docker onboarding)
- Poprawiona obsługa Wake Lock i odtwarzania, aby lepiej działać przy wyłączonym ekranie urządzeń źródłowych i odbiorczych. (commit: Improve wake-lock and playback resilience for screen-off transmission)
- Endpointy health/metrics i walidacja startowa. (commit: Add health check and metrics endpoints with startup validation)
- Zarządzanie sesjami, opcjonalne uwierzytelnianie bearer i lepsze zachowanie podczas rozłączeń/ponownego połączenia. (commit: Enhance WebSocket functionality with session management, authentication, and environment variable configuration)

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

2. Skonfiguruj opcjonalne zmienne środowiskowe dla lokalnego uruchomienia:
   ```bash
   export PORT=8001
   export TLS_ENABLED=true
   export TLS_CERTFILE=cert.pem
   export TLS_KEYFILE=key.pem
   export AUTH_ENABLED=false
   export AUTH_TOKEN=twoj-sekretny-token
   export RECONNECT_GRACE_SECONDS=30
   export CLEANUP_INTERVAL_SECONDS=60
   ```
   W PowerShell użyj `$env:PORT = 8001` dla bieżącej sesji.

3. Wygeneruj certyfikaty:
   ```bash
   openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes \
     -subj "/C=PL/ST=Warsaw/L=Warsaw/O=WebNanny/CN=localhost"
   ```

4. Uruchom serwer:
   ```bash
   python main.py
   ```

5. Otwórz w przeglądarce:
   - `https://<host>:8001/sender`
   - `https://<host>:8001/listener`

### Uruchomienie z Dockerem

1. Utwórz plik `.env` na podstawie `.env.example` i zaktualizuj wartości:
   ```bash
   cp .env.example .env
   ```
   W PowerShell:
   ```powershell
   Copy-Item .env.example .env
   ```

2. TLS i certyfikaty w Docker

- Jeśli `TLS_ENABLED=true` i pliki certyfikatów nie istnieją, aplikacja automatycznie wygeneruje self-signed `cert.pem` i `key.pem` podczas startu kontenera.
- Nie musisz montować certyfikatów z hosta do kontenera do szybkiego testu.
- Jeżeli chcesz użyć własnych certyfikatów, umieść `cert.pem` i `key.pem` w katalogu projektu przed uruchomieniem Dockera i ustaw `TLS_CERTFILE` / `TLS_KEYFILE` w `.env`.

3. Zbuduj obraz:
   ```bash
   docker build -t web_nanny .
   ```

4. Uruchom kontener:
   ```bash
   docker-compose up -d
   ```

5. Otwórz w przeglądarce:
   - `https://<host>:8001/sender`
   - `https://<host>:8001/listener`

## Przepływ użytkowania

1. Przejdź do strony głównej pod adresem `https://<host>:8001`.
2. Wybierz preferowany język (polski lub angielski).
3. Wybierz swoją rolę: Nadajnik (do nadawania dźwięku) lub Odbiornik (do odbioru i monitorowania dźwięku z detekcją płaczu).
4. Postępuj zgodnie z instrukcjami na ekranie, aby rozpocząć/zatrzymać transmisję dźwięku.

## Uwagi

- Nie dodawaj do repozytorium `cert.pem`, `key.pem` ani innych plików z kluczami.
- Projekt jest przeznaczony do zaufanej sieci lokalnej.
- Do produkcji użyj ważnych certyfikatów TLS i dodaj uwierzytelnianie.
