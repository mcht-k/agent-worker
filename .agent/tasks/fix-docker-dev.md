## ZADANIE
Napraw konfigurację docker-compose.dev.yml i Dockerfile'y tak aby wszystkie serwisy Vouchify
uruchomiły się poprawnie. Nie modyfikuj żadnych plików poza tym repo (vouchify-mono).

## KONTEKST ŚRODOWISKA
- VPS z działającym kontenerem nginx-proxy (nie ruszaj go)
- Działający projekt Plannify w osobnych kontenerach (nie ruszaj)
- Sieć vouchify-dev jest izolowana

## AKTUALNE BŁĘDY DO NAPRAWY

### 1. Frontend – npm error
Błąd: `npm error could not determine executable to run`
Przyczyna: `npx ng serve` nie znajduje Angular CLI
Fix: użyj `./node_modules/.bin/ng serve` zamiast `npx ng serve`
Plik: `frontend/Dockerfile.dev`

### 2. Seq – brak hasła admina
Błąd: `No default admin password was supplied`
Fix: dodaj zmienną `SEQ_FIRSTRUN_ADMINPASSWORD=devpassword123` do sekcji environment serwisu seq w docker-compose.dev.yml

## WYMAGANIA
- Wszystkie serwisy muszą wystartować: api, worker, frontend, db, redis, seq
- db i redis już działają poprawnie - nie zmieniaj ich konfiguracji
- api już działa poprawnie - nie zmieniaj jego konfiguracji
- worker już działa poprawnie - nie zmieniaj jego konfiguracji
- Po każdej zmianie uruchom: `docker compose -f docker-compose.dev.yml up --build -d`
- Sprawdź logi każdego serwisu: `docker compose -f docker-compose.dev.yml logs <serwis>`
- Iteruj dopóki wszystkie serwisy nie będą w statusie Up i bez błędów krytycznych
- Frontend jest gotowy gdy w logach pojawi się: `Local: http://localhost:4200`

## WAŻNE
- NIE modyfikuj plików poza tym repo
- NIE restartuj kontenera nginx-proxy
- NIE modyfikuj kontenerów Plannify
- Jeśli frontend potrzebuje długo na `npm install` - poczekaj, to normalne

## DEFINICJA UKOŃCZENIA
Uruchom na końcu:
docker compose -f docker-compose.dev.yml ps
Wszystkie serwisy muszą mieć status `Up`. Wklej wynik do sekcji STATUS.

## STATUS
- [x] Seq fix
- [x] Frontend Dockerfile fix
- [x] Wszystkie serwisy Up

## _STATUS
- stan: completed
- ukończony: 2026-04-11 00:00:00
- notatka: ukończono przed wdrożeniem systemu kolejki
