## ZADANIE
Stwórz encję Tenant, migrację EF Core i podstawowe endpointy CRUD profilu tenanta.

## PLIKI DO PRZECZYTANIA
- backend/Modules/Vouchify.Modules.Identity/
- backend/Vouchify.Infrastructure/

## CO ZROBIĆ
1. W module `Vouchify.Modules.Tenants` stwórz encję `Tenant` z polami: `Id`, `Slug`, `Name`, `LogoUrl`, `Description`, `Status` (enum: Draft, Configured, StripePending, Active, Suspended), `StripeAccountId`, `CreatedAt`
2. Zarejestruj encję w `AppDbContext` z Global Query Filter na `TenantId` (Tenant jest root — nie filtruj po sobie, filtruj pozostałe encje)
3. Dodaj migrację EF Core: `AddTenantEntity`
4. Stwórz command + handler: `UpdateTenantProfileCommand` (Name, Slug, LogoUrl, Description) → zmienia status z Draft na Configured jeśli wszystkie pola wypełnione
5. Stwórz endpoint `PUT /api/tenants/profile` — wymaga roli Owner
6. Stwórz read model `TenantProfileDto` i endpoint `GET /api/tenants/profile`
7. Dodaj stałe błędów `TenantErrors` (SlugTaken, ProfileIncomplete, TenantNotFound)
8. Po zakończeniu wszystkich kroków — zaznacz wszystkie checkboxy w sekcji ## DEFINICJA UKOŃCZENIA w tym pliku na [x]

## PO WYKONANIU

cd ~/projects/vouchify-mono
git add backend/Modules/Vouchify.Modules.Tenants/ backend/Vouchify.Infrastructure/
git commit -m "feat(tenants): tenant entity, migration, profile endpoints"
git push
docker compose -f docker-compose.dev.yml up -d --build api


## DEFINICJA UKOŃCZENIA
- [x] Migracja aplikuje się bez błędów (tenants table w Initial migration)
- [x] `GET /api/tenants/profile` zwraca dane tenanta
- [x] `PUT /api/tenants/profile` aktualizuje profil i zmienia status na Configured
- [x] `TenantErrors` zdefiniowane
## _STATUS
- stan: completed
- ukończony: 2026-04-11 10:27:00
- notatka: wszystkie zadania ukończone, kod zacommitowany
