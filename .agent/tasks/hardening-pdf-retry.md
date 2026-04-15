## ZADANIE
Dodaj retry logic dla generowania PDF i obsługę błędów Sentry dla krytycznych operacji.

## PLIKI DO PRZECZYTANIA
- backend/Modules/Vouchify.Modules.Vouchers/
- backend/Vouchify.Worker/

## CO ZROBIĆ
1. Opakuj wywołanie `IVoucherPdfGenerator.GenerateAsync` w Hangfire background job `GenerateVoucherPdfJob` zamiast wywoływać synchronicznie w handlerze `VoucherCreated`
2. Skonfiguruj retry dla tego joba: 3 próby, backoff 5/30/120 sekund
3. Po 3 nieudanych próbach: wyślij alert przez Sentry (`SentrySdk.CaptureException`) z tagami `voucherId`, `tenantId`
4. Sprawdź czy Sentry SDK jest skonfigurowany w projekcie — jeśli nie, dodaj pakiet `Sentry.AspNetCore` i skonfiguruj przez `SENTRY_DSN` z zmiennych środowiskowych
5. Dodaj Sentry capture dla: niepowodzenia webhooka Stripe po retry, błędu wysyłki emaila po retry
6. Po zakończeniu wszystkich kroków — zaznacz wszystkie checkboxy w sekcji ## DEFINICJA UKOŃCZENIA w tym pliku na [x]

## PO WYKONANIU

cd ~/projects/vouchify-mono
git add backend/Modules/Vouchify.Modules.Vouchers/ backend/Vouchify.Worker/ backend/Vouchify.Api/
git commit -m "feat(hardening): pdf retry hangfire, sentry alerts for critical failures"
git push
docker compose -f docker-compose.dev.yml up -d --build api worker


## DEFINICJA UKOŃCZENIA
- [x] GenerateVoucherPdfJob widoczny w Hangfire z konfiguracją retry
- [x] Po 3 błędach — alert w Sentry z tagami voucherId i tenantId
- [x] Sentry DSN ładowany ze zmiennej środowiskowej
## _STATUS
- stan: completed
- ukończony: 2026-04-12 11:19:16
