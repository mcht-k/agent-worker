## ZADANIE
Przeczytaj wszystkie pliki konfiguracyjne w repo i zaktualizuj CLAUDE.md o informacje
o infrastrukturze i konfiguracji środowiska dev. Następnie zrób commit.

## CO PRZECZYTAĆ
- docker-compose.dev.yml
- backend/Dockerfile.dev
- backend/Dockerfile.worker.dev
- frontend/Dockerfile.dev
- frontend/angular.json (sekcja allowedHosts)
- .env.dev.example
- backend/migrate.sh
- .agent/run.sh

## CO DODAĆ DO CLAUDE.md

### Sekcja: Infrastruktura VPS
- VPS z Docker, nginx-proxy kontener jako reverse proxy
- Konfiguracje Nginx: /opt/nginx/conf.d/ na hoście (bind mount do kontenera)
- Certyfikaty SSL: /etc/letsencrypt/ na hoście (bind mount do kontenera, read-only)
- Sieć dev_internal: wspólna sieć dla nginx-proxy i kontenerów dev
- Plannify (inny projekt) działa na tym samym VPS - nie ruszać

### Sekcja: Środowisko dev
- URL frontend: https://dev.vouchify.mtlabs.pl
- URL API: https://api.dev.vouchify.mtlabs.pl
- Uruchomienie: docker compose -f docker-compose.dev.yml up -d
- Logi: docker compose -f docker-compose.dev.yml logs -f <serwis>
- Serwisy: api (5200), worker, frontend (4200), db (postgres:16), redis (7), seq (8081)
- Seq UI: http://VPS_IP:8081 (hasło: SEQ_FIRSTRUN_ADMINPASSWORD z .env.dev)
- Angular allowedHosts: ustawione przez angular.json ("allowedHosts": true), nie przez flagę CLI

### Sekcja: Ważne zasady dla agenta
- Po każdym docker compose up --build kontenery tracą połączenie z dev_internal
- Sieć dev_internal jest zadeklarowana w docker-compose.dev.yml jako external - działa automatycznie
- Nigdy nie modyfikuj kontenerów: nginx-proxy, plannify-*
- Nigdy nie modyfikuj plików w /opt/nginx/conf.d/ bez wyraźnej potrzeby
- Nowe serwisy wymagają dodania do sieci dev_internal w docker-compose.dev.yml

### Sekcja: Agent
- Skrypt: .agent/run.sh
- Task filee: .agent/tasks/
- Logi: .agent/agent.log
- Powiadomienia: ntfy.sh przez NOTIFY_URL z ~/.bashrc

## PO AKTUALIZACJI CLAUDE.md
Wykonaj:
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with VPS infrastructure and dev environment config"
git push

## DEFINICJA UKOŃCZENIA
- CLAUDE.md zawiera wszystkie sekcje
- git log pokazuje nowy commit
- Wyświetl ostatnie 20 linii CLAUDE.md

## STATUS
- [x] CLAUDE.md zaktualizowany
- [x] commit zrobiony
- [x] push zrobiony

## _STATUS
- stan: completed
- ukończony: 2026-04-11 00:00:00
- notatka: ukończono przed wdrożeniem systemu kolejki
