## ZADANIE
Stwórz docker-compose.dev.yml dla środowiska developerskiego projektu Vouchify.

## STRUKTURA REPO
- `backend/` – .NET 10 Minimal API (Vouchify.Api), Worker (Vouchify.Worker)
- `frontend/` – Angular 21

## WYMAGANIA

### Serwisy do uruchomienia
1. **api** – Vouchify.Api, port 5200, hot reload (`dotnet watch`)
2. **worker** – Vouchify.Worker, Hangfire
3. **frontend** – Angular dev server, port 4200, hot reload (`ng serve --host 0.0.0.0`)
4. **db** – PostgreSQL 16, port tylko wewnętrzny, volume na dane
5. **redis** – Redis 7 Alpine, tylko wewnętrzny
6. **seq** – Datalust Seq, port 5341 (UI: 8081)

### Wymagania techniczne
- Osobna named network: `vouchify-dev`
- db i redis NIE wystawiają portów na host
- Hot reload działa przez bind mount całego folderu backend/ i frontend/
- Zmienne środowiskowe przez env_file: `.env.dev` (stwórz przykładowy `.env.dev.example`)
- api i worker zależą od db i redis (depends_on z condition: service_healthy)
- Healthcheck dla db (pg_isready) i redis (redis-cli ping)

### .env.dev.example – zmienne do stworzenia

ASPNETCORE_ENVIRONMENT=Development
ConnectionStrings__DefaultConnection=Host=db;Database=vouchify_dev;Username=vouchify;Password=devpassword
Redis__ConnectionString=redis:6379
Seq__ServerUrl=http://seq:5341
Hangfire__Dashboard=true

### Dockerfile.dev dla backendu
Stwórz `backend/Dockerfile.dev`:
- Base image: mcr.microsoft.com/dotnet/sdk:10.0
- Zainstaluj dotnet-ef global tool
- ENTRYPOINT: dotnet watch run z projektu Vouchify.Api

### Dockerfile.dev dla workera
Stwórz `backend/Dockerfile.worker.dev`:
- Base image: mcr.microsoft.com/dotnet/sdk:10.0
- ENTRYPOINT: dotnet watch run z projektu Vouchify.Worker

### Dockerfile.dev dla frontendu
Stwórz `frontend/Dockerfile.dev`:
- Base image: node:20-alpine
- npm install przy starcie jeśli node_modules nie istnieje
- ENTRYPOINT: ng serve --host 0.0.0.0 --poll 2000

## MIGRACJE
Stwórz skrypt `backend/migrate.sh`:
- Uruchamia `dotnet ef database update` dla AppDbContext
- Używa connection string z env

## DEFINICJA UKOŃCZENIA
- docker-compose.dev.yml istnieje w root repo
- Wszystkie Dockerfile.dev istnieją
- .env.dev.example istnieje z wszystkimi zmiennymi
- migrate.sh istnieje i jest wykonywalny
- Przejrzyj pliki pod kątem błędów konfiguracyjnych zanim skończysz

## STATUS
- [x] docker-compose.dev.yml
- [x] backend/Dockerfile.dev
- [x] backend/Dockerfile.worker.dev
- [x] frontend/Dockerfile.dev
- [x] backend/migrate.sh
- [x] .env.dev.example

## _STATUS
- stan: completed
- ukończony: 2026-04-11 00:00:00
- notatka: ukończono przed wdrożeniem systemu kolejki
