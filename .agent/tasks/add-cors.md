## ZADANIE
Dodaj konfigurację CORS do backendu (.NET 10 Minimal API) bez hardcodowania domen.

## WYMAGANIA
- Domeny CORS czytane z konfiguracji (appsettings), nie hardcodowane w kodzie
- Obsługa wielu domen (tablica)
- Różne wartości per środowisko (appsettings.Development.json vs appsettings.json)

## CO ZROBIĆ

### 1. appsettings.json (produkcja - placeholder)
```json
"Cors": {
  "AllowedOrigins": []
}
```

### 2. appsettings.Development.json
```json
"Cors": {
  "AllowedOrigins": [
    "https://dev.vouchify.mtlabs.pl",
    "http://localhost:4200"
  ]
}
```

### 3. Program.cs
- Wczytaj AllowedOrigins z konfiguracji
- Zarejestruj politykę CORS z tymi domenami
- Dodaj `app.UseCors()` w pipeline (przed UseAuthorization)
- Jeśli AllowedOrigins jest puste - rzuć wyjątek przy starcie (fail fast)

### 4. Po zakończeniu wszystkich kroków — zaznacz wszystkie checkboxy w sekcji ## STATUS w tym pliku na [x]

## WERYFIKACJA
Po zmianach sprawdź czy API się kompiluje i startuje:
docker compose -f docker-compose.dev.yml logs api 2>&1 | tail -20

## COMMIT
git add .
git commit -m "feat: add CORS configuration from appsettings"
git push

## STATUS
- [x] appsettings.json zaktualizowany
- [x] appsettings.Development.json zaktualizowany
- [x] Program.cs zaktualizowany
- [x] API startuje bez błędów
- [x] commit i push zrobiony

## _STATUS
- stan: completed
- ukończony: 2026-04-11 00:00:00
- notatka: ukończono przed wdrożeniem systemu kolejki
