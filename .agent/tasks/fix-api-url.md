## ZADANIE
Znajdź i popraw konfigurację URL API dla środowiska dev w projekcie Angular (frontend/).
Następnie zrób commit i push.

## PROBLEM
Frontend wskazuje na localhost zamiast https://api.dev.vouchify.mtlabs.pl

## GDZIE SZUKAĆ
Przejrzyj w tej kolejności:
- frontend/src/environments/environment.ts
- frontend/src/environments/environment.development.ts
- frontend/src/app/core/services/ (serwisy HTTP)
- frontend/src/app/app.config.ts
- angular.json (fileReplacements)

## CO ZMIENIĆ
Znajdź gdzie jest zdefiniowany baseUrl/apiUrl i ustaw:
- development: https://api.dev.vouchify.mtlabs.pl
- production: zostaw bez zmian lub zostaw placeholder

## WERYFIKACJA
Po zmianie sprawdź czy Angular się kompiluje:
docker compose -f docker-compose.dev.yml logs -f frontend 2>&1 | grep -E "Local:|error|Error" | head -5

## COMMIT
git add .
git commit -m "fix: set dev API URL to api.dev.vouchify.mtlabs.pl"
git push

## STATUS
- [x] Znaleziono miejsce konfiguracji API URL
- [x] URL zmieniony na https://api.dev.vouchify.mtlabs.pl
- [x] Angular kompiluje się bez błędów
- [x] commit i push zrobiony

## _STATUS
- stan: completed
- ukończony: 2026-04-11 00:00:00
- notatka: ukończono przed wdrożeniem systemu kolejki
