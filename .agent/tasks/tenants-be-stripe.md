## ZADANIE
Zaimplementuj Stripe Connect Express onboarding dla tenanta: inicjowanie, webhook i Hangfire reminder.

## PLIKI DO PRZECZYTANIA
- backend/Modules/Vouchify.Modules.Tenants/
- backend/Vouchify.Worker/

## CO ZROBIĆ
1. Stwórz command `InitiateStripeOnboardingCommand` → wywołuje Stripe API `AccountLinks.Create` z typem `account_onboarding`, zmienia status tenanta na StripePending, zwraca URL
2. Stwórz endpoint `POST /api/tenants/stripe/onboarding` → zwraca `{ url: "https://connect.stripe.com/..." }` — wymaga statusu Configured
3. Stwórz endpoint `POST /api/webhooks/stripe/connect` (bez autoryzacji JWT) — obsługuje event `account.updated`: jeśli `charges_enabled == true` → zmienia status tenanta na Active
4. Zabezpiecz webhook weryfikacją Stripe-Signature (Stripe.WebhookSecret z konfiguracji)
5. W `Vouchify.Worker` stwórz Hangfire job `SendStripeReminderJob`: znajduje tenantów ze statusem StripePending przez ponad 24h → wysyła email przez `INotificationService` z template `StripeOnboardingReminder`
6. Zarejestruj job jako `RecurringJob` co 1 godzinę
7. Po zakończeniu wszystkich kroków — zaznacz wszystkie checkboxy w sekcji ## DEFINICJA UKOŃCZENIA w tym pliku na [x]

## PO WYKONANIU

cd ~/projects/vouchify-mono
git add backend/Modules/Vouchify.Modules.Tenants/ backend/Vouchify.Worker/
git commit -m "feat(tenants): stripe connect onboarding, webhook, hangfire reminder"
git push
docker compose -f docker-compose.dev.yml up -d --build api worker


## DEFINICJA UKOŃCZENIA
- [x] `POST /api/tenants/stripe/onboarding` zwraca redirect URL
- [x] Webhook `account.updated` zmienia status na Active
- [x] Weryfikacja Stripe-Signature nie przepuszcza fałszywych requestów
- [x] Hangfire job widoczny w dashboardzie `/admin/jobs`
## _STATUS
- stan: completed
- zakończony: 2026-04-11
