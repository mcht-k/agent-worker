## ZADANIE
Stwórz encję Voucher, generowanie unikalnego kodu po zdarzeniu OrderPaid i endpointy weryfikacji.

## PLIKI DO PRZECZYTANIA
- backend/Modules/Vouchify.Modules.Vouchers/
- backend/Modules/Vouchify.Modules.Orders/
- backend/Vouchify.Infrastructure/

## CO ZROBIĆ
1. Stwórz encję `Voucher` z polami: `Id`, `TenantId`, `OrderId`, `VoucherTypeId`, `Code` (string, unikalny), `Status` (enum: Active, Used, Expired), `ValidUntil` (DateOnly), `UsedAt` (nullable DateTime), `CreatedAt`
2. Migracja: `AddVoucherEntity`
3. Handler dla eventu `OrderPaid`:
   - Generuj unikalny kod: 12 znaków, alfanumeryczny, wielkie litery (np. `ABCD-1234-EFGH`)
   - Oblicz `ValidUntil`: jeśli VoucherType.ValidityDays != null → Today + ValidityDays, else VoucherType.ValidUntil
   - Zapisz Voucher ze statusem Active
   - Publikuj event `VoucherCreated`
4. Command `VerifyVoucherCommand` (Code lub QR payload) → zwraca `VoucherDetailsDto` (szczegóły vouchera + dane zamówienia) lub błąd
5. Command `RedeemVoucherCommand` (Code) → zmienia status na Used, ustawia UsedAt — waliduje: tylko Active, nie Expired
6. Hangfire job `ExpireVouchersJob` — codziennie o 00:05 — ustawia status Expired dla voucherów gdzie ValidUntil < Today i Status == Active
7. Endpointy (wymagają JWT, rola Owner lub Employee):
   - `POST /api/vouchers/verify`
   - `POST /api/vouchers/redeem`
   - `GET /api/vouchers` — lista z filtrami (Status, DateFrom, DateTo, VoucherTypeId)
   - `GET /api/vouchers/{id}` — szczegóły
8. Dodaj stałe błędów `VoucherErrors` (VoucherNotFound, AlreadyUsed, Expired, InvalidCode)
9. Po zakończeniu wszystkich kroków — zaznacz wszystkie checkboxy w sekcji ## DEFINICJA UKOŃCZENIA w tym pliku na [x]

## PO WYKONANIU

cd ~/projects/vouchify-mono
git add backend/Modules/Vouchify.Modules.Vouchers/ backend/Vouchify.Infrastructure/
git commit -m "feat(vouchers): voucher entity, code generation, verify, redeem, expire job"
git push
docker compose -f docker-compose.dev.yml up -d --build api worker


## DEFINICJA UKOŃCZENIA
- [x] Voucher tworzony automatycznie po OrderPaid
- [x] Unikalność kodu zapewniona (unique index w bazie)
- [x] Weryfikacja zwraca szczegóły lub odpowiedni błąd
- [x] Realizacja zmienia status na Used
- [x] Hangfire job ExpireVouchersJob widoczny w dashboardzie
## _STATUS
- stan: completed
- ukończony: 2026-04-12 01:09:15
