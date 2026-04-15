## ZADANIE
Stwórz dokumentację techniczną projektu Vouchify w katalogu docs/ — architektura, moduły, API i instrukcja uruchomienia.

## PLIKI DO PRZECZYTANIA
- backend/Modules/
- backend/Vouchify.Api/
- docker-compose.dev.yml
- docs/security-review.md

## CO ZROBIĆ
1. Stwórz docs/README.md — główny dokument z krótkim opisem projektu i linkami do pozostałych dokumentów

2. Stwórz docs/architecture.md zawierający: diagram tekstowy ASCII architektury systemu, opis wzorca Modulith i CQRS, opis każdego modułu i jego odpowiedzialności, model multi-tenancy (AppDbContext, Global Query Filters, slug cache Redis), schemat flow zakupu vouchera end-to-end, schemat statusów tenanta i vouchera

3. Stwórz docs/api.md zawierający: listę wszystkich endpointów pogrupowaną per moduł, dla każdego endpointu metodę/ścieżkę/autoryzację/krótki opis, opis webhooków Stripe, opis formatu błędów z polami code/message/details/traceId

4. Stwórz docs/development.md zawierający: wymagania (Docker, .NET 10, Node), instrukcję uruchomienia przez docker compose, opis zmiennych środowiskowych z .env.dev, instrukcję dodawania migracji EF Core, opis systemu kolejkowania agenta w katalogu .agent/

5. Po zakończeniu zaznacz wszystkie checkboxy w sekcji DEFINICJA UKOŃCZENIA na [x]

## PO WYKONANIU
cd ~/projects/vouchify-mono
git add docs/
git commit -m "docs: technical documentation - architecture, api, development guide"
git push

## DEFINICJA UKOŃCZENIA
- [x] docs/README.md z linkami do pozostałych dokumentów
- [x] docs/architecture.md z diagramem i opisem modułów
- [x] docs/api.md z listą wszystkich endpointów
- [x] docs/development.md z instrukcją uruchomienia
- [x] Commit i push wykonany
## _STATUS
- stan: completed
- ukończony: 2026-04-12 16:49:54
