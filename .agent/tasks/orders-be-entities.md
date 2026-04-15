## ZADANIE
Stwórz encję Order z powiązaniami i migracją EF Core.

## PLIKI DO PRZECZYTANIA
- backend/Modules/Vouchify.Modules.Orders/
- backend/Modules/Vouchify.Modules.Catalog/
- backend/Vouchify.Infrastructure/

## CO ZROBIĆ
1. Stwórz encję `Order` z polami: `Id`, `TenantId`, `VoucherTypeId`, `BuyerEmail`, `BuyerName`, `RecipientEmail` (nullable), `RecipientName` (nullable), `Amount` (decimal), `Status` (enum: Pending, Paid, Failed, Refunded), `StripeSessionId`, `StripePaymentIntentId`, `CreatedAt`
2. Relacja: `Order` → `VoucherType` (nie usuwaj kaskadowo)
3. Stwórz value object `Money` (Amount + Currency) jeśli nie istnieje w Core
4. Zarejestruj w AppDbContext z Global Query Filter na TenantId
5. Dodaj migrację: `AddOrderEntity`
6. Dodaj stałe błędów `OrderErrors` (OrderNotFound, PaymentFailed, AlreadyRefunded, RefundFailed)
7. Po zakończeniu wszystkich kroków — zaznacz wszystkie checkboxy w sekcji ## DEFINICJA UKOŃCZENIA w tym pliku na [x]

## PO WYKONANIU

cd ~/projects/vouchify-mono
git add backend/Modules/Vouchify.Modules.Orders/ backend/Vouchify.Infrastructure/
git commit -m "feat(orders): order entity, migration, error constants"
git push
docker compose -f docker-compose.dev.yml up -d --build api


## DEFINICJA UKOŃCZENIA
- [x] Migracja aplikuje się bez błędów
- [x] Relacja Order → VoucherType poprawna w bazie
- [x] Global Query Filter na TenantId działa
## _STATUS
- stan: completed
- ukończony: 2026-04-11 16:11:07
