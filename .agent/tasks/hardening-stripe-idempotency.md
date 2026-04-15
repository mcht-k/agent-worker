## ZADANIE
Zweryfikuj i uodpornij obsługę webhooków Stripe na duplikaty — tabela ProcessedStripeEvents powinna działać dla obu webhooków (connect i payments).

## PLIKI DO PRZECZYTANIA
- backend/Modules/Vouchify.Modules.Orders/
- backend/Modules/Vouchify.Modules.Tenants/
- backend/Vouchify.Infrastructure/

## CO ZROBIĆ
1. Sprawdź czy tabela `ProcessedStripeEvents` istnieje i jest używana w obu handlerach webhooków (`/api/webhooks/stripe/connect` i `/api/webhooks/stripe/payments`)
2. Jeśli nie — stwórz encję `ProcessedStripeEvent` (EventId, EventType, ProcessedAt) + migracja
3. Upewnij się że sprawdzenie duplikatu i zapis są w jednej transakcji (unique constraint na EventId)
4. Dodaj indeks na `ProcessedAt` do czyszczenia starych eventów
5. Stwórz Hangfire job `CleanOldStripeEventsJob` — usuwa rekordy starsze niż 30 dni, uruchamiany co tydzień
6. Po zakończeniu wszystkich kroków — zaznacz wszystkie checkboxy w sekcji ## DEFINICJA UKOŃCZENIA w tym pliku na [x]

## PO WYKONANIU

cd ~/projects/vouchify-mono
git add backend/Modules/Vouchify.Modules.Orders/ backend/Modules/Vouchify.Modules.Tenants/ backend/Vouchify.Infrastructure/
git commit -m "fix(hardening): stripe webhook idempotency, cleanup job"
git push
docker compose -f docker-compose.dev.yml up -d --build api worker


## DEFINICJA UKOŃCZENIA
- [x] Drugi webhook z tym samym EventId jest ignorowany
- [x] Unique constraint na EventId w bazie
- [x] CleanOldStripeEventsJob widoczny w Hangfire
## _STATUS
- stan: completed
- ukończony: 2026-04-12 06:12:15
- notatka: wszystkie checkboxy zaznaczone, proces ubity SIGTERM po wykonaniu
