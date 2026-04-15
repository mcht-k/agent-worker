## ZADANIE
Uprość formularz rejestracji i zaktualizuj treść emaili rejestracyjnych.

## ZAKRES
- frontend/src/ — formularz rejestracji
- backend/Modules/Vouchify.Modules.Identity/ — command/model rejestracji
- backend/Modules/Vouchify.Modules.Notifications/Templates/AccountActivation.cshtml
- backend/Modules/Vouchify.Modules.Notifications/Templates/AccountActivated.cshtml

## ZMIANY FE — formularz rejestracji
Znajdź komponent rejestracji i zostaw TYLKO dwa pola:
- email
- hasło

Usuń wszystkie inne pola (imię, nazwisko, nazwa firmy, telefon, cokolwiek innego).
Zachowaj istniejący styl i design system — tylko usuń pola, nie przepisuj komponentu.

## ZMIANY BE — command/model rejestracji
Znajdź RegisterCommand (lub analogiczny) w module Identity.
Usuń z modelu wszystkie pola poza:
- Email
- Password

Usuń też walidacje FluentValidation dla usuniętych pól.
Jeśli inne pola są wymagane w bazie danych — ustaw im wartości domyślne (pusty string lub null).

## ZMIANY EMAILI — ton bezosobowy
Edytuj tylko te dwa szablony:
- AccountActivation.cshtml — email z linkiem aktywacyjnym wysyłany po rejestracji
- AccountActivated.cshtml — email potwierdzający aktywację konta

Zasady:
- Bezosobowy ton — bez "Drogi [imię]", bez personalnych zwrotów
- Nie używaj żadnych zmiennych z imieniem/nazwiskiem
- Przykładowe zwroty: "Dziękujemy za rejestrację", "Konto zostało aktywowane", "Aby aktywować konto kliknij poniższy link"
- Zachowaj istniejący layout (_Layout.cshtml, _Header.cshtml, _Footer.cshtml) — nie modyfikuj shared templates
- Zachowaj wszystkie zmienne techniczne (link aktywacyjny, tokeny itp.)

## WERYFIKACJA
docker compose -f docker-compose.dev.yml logs api 2>&1 | tail -10
docker compose -f docker-compose.dev.yml logs frontend 2>&1 | grep -E "Local:|error" | tail -5

## COMMIT
git add .
git commit -m "feat: simplify registration form to email+password only, update email templates to impersonal tone"
git push

## STATUS
- [x] Formularz FE — tylko email i hasło
- [x] RegisterCommand BE — tylko Email i Password
- [x] AccountActivation.cshtml — bezosobowy ton
- [x] AccountActivated.cshtml — bezosobowy ton
- [x] API kompiluje się bez błędów
- [x] Frontend kompiluje się bez błędów
- [x] commit i push zrobiony

## _STATUS
- stan: completed
- ukończony: 2026-04-11 00:00:00
- notatka: ukończono przed wdrożeniem systemu kolejki
