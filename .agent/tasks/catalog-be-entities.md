## ZADANIE
Stwórz encję VoucherType z konfiguracją kwotową/produktową i migracją EF Core.

## PLIKI DO PRZECZYTANIA
- backend/Modules/Vouchify.Modules.Catalog/
- backend/Vouchify.Infrastructure/

## CO ZROBIĆ
1. Stwórz encję `VoucherType` z polami: `Id`, `TenantId`, `Name`, `Description`, `Type` (enum: Amount, Product), `IsVisible`, `SortOrder`, `ValidityDays` (nullable int), `ValidUntil` (nullable DateOnly), `CreatedAt`
2. Dla typu Amount — stwórz owned type `AmountConfig`: `Mode` (enum: FixedList, FreeAmount, Slider), `FixedValues` (int[], JSON), `SliderMin` (int), `SliderMax` (int)
3. Dla typu Product — stwórz owned type `ProductConfig`: `ProductName`, `ProductDescription`, `ImageUrl`, `Price` (decimal)
4. Stwórz encję `PdfConfig` (owned by VoucherType): `TemplateId` (1–5), `ShowAmount` (bool), `ShowDescription` (bool), `ShowQrCode` (bool), `ShowLink` (bool), `ShowExpiryDate` (bool)
5. Zarejestruj w AppDbContext z Global Query Filter na TenantId
6. Dodaj migrację: `AddVoucherTypeEntity`
7. Dodaj stałe błędów `CatalogErrors` (VoucherTypeLimitReached, VoucherTypeNotFound, InvalidAmountConfig)
8. Po zakończeniu wszystkich kroków — zaznacz wszystkie checkboxy w sekcji ## DEFINICJA UKOŃCZENIA w tym pliku na [x]

## PO WYKONANIU

cd ~/projects/vouchify-mono
git add backend/Modules/Vouchify.Modules.Catalog/ backend/Vouchify.Infrastructure/
git commit -m "feat(catalog): voucher type entity, owned types, migration"
git push
docker compose -f docker-compose.dev.yml up -d --build api


## DEFINICJA UKOŃCZENIA
- [x] Migracja aplikuje się bez błędów
- [x] Encja VoucherType z owned types zapisuje się do bazy
- [x] Global Query Filter na TenantId działa
## _STATUS
- stan: completed
- ukończony: 2026-04-11 15:29:36
