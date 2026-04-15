## ZADANIE
Stwórz widok checklisty onboardingu tenanta w panelu Angular z formularzem profilu i przyciskiem uruchomienia sprzedaży.

## PLIKI DO PRZECZYTANIA
- frontend/src/app/features/auth/
- frontend/src/app/

## CO ZROBIĆ
1. Stwórz feature `onboarding` w `frontend/src/app/features/onboarding/`
2. Stwórz komponent `OnboardingChecklistComponent` — wyświetla kroki: (1) Uzupełnij profil, (2) Połącz Stripe, (3) Konto aktywne — każdy krok z ikoną statusu (pending/done)
3. Stwórz formularz `TenantProfileFormComponent` — pola: Nazwa biznesu, Slug (z podglądem URL: `dev.vouchify.mtlabs.pl/t/{slug}`), Logo URL, Opis — `PUT /api/tenants/profile`
4. Przycisk „Uruchom sprzedaż" — aktywny tylko gdy status === 'Configured' → `POST /api/tenants/stripe/onboarding` → redirect do zwróconego URL
5. Badge statusu konta w nagłówku panelu (Draft / Configured / Oczekuje na Stripe / Aktywny / Zawieszony)
6. Po powrocie ze Stripe (query param `?stripe=success`) — odśwież status i pokaż komunikat sukcesu
7. Routing: `/panel/onboarding` — przekieruj tu po logowaniu jeśli status != Active
8. Po zakończeniu wszystkich kroków — zaznacz wszystkie checkboxy w sekcji ## DEFINICJA UKOŃCZENIA w tym pliku na [x]

## PO WYKONANIU

cd ~/projects/vouchify-mono
git add frontend/src/app/features/onboarding/
git commit -m "feat(tenants-fe): onboarding checklist, profile form, stripe redirect"
git push
docker compose -f docker-compose.dev.yml up -d --build frontend


## DEFINICJA UKOŃCZENIA
- [x] Checklist wyświetla aktualny status kroków
- [x] Formularz profilu zapisuje dane i odświeża status
- [x] Przycisk „Uruchom sprzedaż" przekierowuje do Stripe
- [x] Badge statusu widoczny w nagłówku
## _STATUS
- stan: completed
- ukończony: 2026-04-12 07:32:39
