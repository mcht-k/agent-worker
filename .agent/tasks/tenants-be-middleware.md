## ZADANIE
Dodaj middleware blokujący endpointy sprzedażowe dla tenantów z statusem innym niż Active.

## PLIKI DO PRZECZYTANIA
- backend/Modules/Vouchify.Modules.Tenants/
- backend/Vouchify.Api/

## CO ZROBIĆ
1. Stwórz middleware `TenantStatusMiddleware` który dla ścieżek zaczynających się od `/t/` sprawdza status tenanta (z Redis cache TTL 5 min, klucz: `tenant:slug:{slug}`)
2. Jeśli status != Active → zwróć `403` z `AppException` code `TENANT_INACTIVE`
3. Dla ścieżek `/api/` z JWT — sprawdź status tenanta z claima `TenantId` (cache klucz: `tenant:id:{tenantId}`)
4. Zarejestruj middleware w pipeline przed endpointami (po autentykacji)
5. Dodaj helper `ITenantStatusCache` z metodami `GetBySlugAsync` i `GetByIdAsync` i `InvalidateAsync` — InvalidateAsync wywoływany przy każdej zmianie statusu
6. Po zakończeniu wszystkich kroków — zaznacz wszystkie checkboxy w sekcji ## DEFINICJA UKOŃCZENIA w tym pliku na [x]

## PO WYKONANIU

cd ~/projects/vouchify-mono
git add backend/Vouchify.Api/ backend/Modules/Vouchify.Modules.Tenants/
git commit -m "feat(tenants): tenant status middleware with redis cache"
git push
docker compose -f docker-compose.dev.yml up -d --build api


## DEFINICJA UKOŃCZENIA
- [x] Request do `/t/{slug}` gdy tenant Suspended zwraca 403
- [x] Cache Redis ustawia TTL 5 min
- [x] InvalidateAsync wywoływany przy zmianie statusu tenanta
## _STATUS
- stan: completed
- ukończony: 2026-04-11 10:33:28
- notatka: commit 9e11cbc — feat(tenants): tenant status middleware with redis cache
