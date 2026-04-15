## ZADANIE
Dodaj rate limiting na publicznych endpointach sprzedażowych żeby zapobiec nadużyciom.

## PLIKI DO PRZECZYTANIA
- backend/Vouchify.Api/
- backend/Modules/Vouchify.Modules.Orders/

## CO ZROBIĆ
1. Użyj wbudowanego .NET 7+ Rate Limiting middleware (`Microsoft.AspNetCore.RateLimiting`)
2. Stwórz politykę `storefront-policy`: 60 requestów / minutę per IP, sliding window
3. Stwórz politykę `checkout-policy`: 5 requestów / minutę per IP, fixed window — agresywniejsza dla endpointu zakupu
4. Zastosuj `storefront-policy` do wszystkich ścieżek `/t/{slug}/*`
5. Zastosuj `checkout-policy` do `POST /t/{slug}/orders/checkout`
6. Odpowiedź 429 w formacie `AppException` z code `RATE_LIMIT_EXCEEDED`
7. Po zakończeniu wszystkich kroków — zaznacz wszystkie checkboxy w sekcji ## DEFINICJA UKOŃCZENIA w tym pliku na [x]

## PO WYKONANIU

cd ~/projects/vouchify-mono
git add backend/Vouchify.Api/
git commit -m "feat(hardening): rate limiting storefront and checkout endpoints"
git push
docker compose -f docker-compose.dev.yml up -d --build api


## DEFINICJA UKOŃCZENIA
- [x] 6. request do checkout w ciągu minuty zwraca 429
- [x] Odpowiedź 429 w formacie AppException JSON
- [x] Endpointy panelu nie są objęte rate limitingiem
## _STATUS
- stan: completed
- ukończony: 2026-04-12
