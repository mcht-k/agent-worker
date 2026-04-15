## ZADANIE
Dodaj zewnętrzną sieć dev_internal do docker-compose.dev.yml.

## CO ZROBIĆ
1. W sekcji `networks` na końcu pliku dodaj:
```yaml
  dev_internal:
    external: true
```

2. Do serwisu `frontend` dodaj sieć `dev_internal`:
```yaml
    networks:
      - vouchify-dev
      - dev_internal
```

3. Do serwisu `api` dodaj sieć `dev_internal`:
```yaml
    networks:
      - vouchify-dev
      - dev_internal
```

4. Uruchom:
docker compose -f docker-compose.dev.yml up -d --no-build frontend api

5. Sprawdź czy DNS działa:
docker exec nginx-proxy nslookup vouchify_frontend_dev 127.0.0.11

6. Sprawdź HTTP:
curl -s -o /dev/null -w "%{http_code}" https://dev.vouchify.mtlabs.pl
7. Po zakończeniu wszystkich kroków — zaznacz wszystkie checkboxy w sekcji ## DEFINICJA UKOŃCZENIA w tym pliku na [x]

## DEFINICJA UKOŃCZENIA
curl zwraca 200. Wklej wynik do STATUS.

## STATUS
- [x] docker-compose.dev.yml zaktualizowany
- [x] kontenery zrestartowane
- [x] curl zwraca 200

## _STATUS
- stan: completed
- ukończony: 2026-04-11 00:00:00
- notatka: ukończono przed wdrożeniem systemu kolejki
