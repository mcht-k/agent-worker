## ZADANIE
Stwórz CQRS commands/queries i endpointy REST dla zarządzania typami voucherów przez właściciela oraz publiczny endpoint strony oferty.

## PLIKI DO PRZECZYTANIA
- backend/Modules/Vouchify.Modules.Catalog/
- backend/Modules/Vouchify.Modules.Tenants/

## CO ZROBIĆ
1. Commands: `CreateVoucherTypeCommand`, `UpdateVoucherTypeCommand`, `DeleteVoucherTypeCommand`, `ReorderVoucherTypesCommand` (lista Id z nową kolejnością), `ToggleVoucherTypeVisibilityCommand`
2. Queries: `GetVoucherTypesQuery` (lista dla panelu), `GetPublicVoucherTypesQuery` (lista publiczna — tylko IsVisible=true, wg SortOrder), `GetVoucherTypeByIdQuery`
3. Walidacja: sprawdź miękki limit typów voucherów per tenant (domyślnie 10, z `AppSettings:VoucherTypeLimit`) w `CreateVoucherTypeCommand`
4. Endpointy panelu (wymagają JWT + rola Owner):
   - `GET /api/catalog/voucher-types`
   - `POST /api/catalog/voucher-types`
   - `PUT /api/catalog/voucher-types/{id}`
   - `DELETE /api/catalog/voucher-types/{id}`
   - `PUT /api/catalog/voucher-types/reorder`
   - `PATCH /api/catalog/voucher-types/{id}/visibility`
5. Endpoint publiczny (bez JWT, tylko slug z middleware):
   - `GET /t/{slug}/vouchers` — zwraca `PublicVoucherTypeDto[]`
6. Po zakończeniu wszystkich kroków — zaznacz wszystkie checkboxy w sekcji ## DEFINICJA UKOŃCZENIA w tym pliku na [x]

## PO WYKONANIU

cd ~/projects/vouchify-mono
git add backend/Modules/Vouchify.Modules.Catalog/
git commit -m "feat(catalog): CQRS commands, queries, REST endpoints"
git push
docker compose -f docker-compose.dev.yml up -d --build api


## DEFINICJA UKOŃCZENIA
- [x] CRUD voucherów działa w panelu
- [x] Reorder zmienia SortOrder w bazie
- [x] Limit typów blokuje tworzenie powyżej progu
- [x] `GET /t/{slug}/vouchers` zwraca tylko widoczne vouchery
## _STATUS
- stan: completed
- ukończony: 2026-04-11 16:06:22
