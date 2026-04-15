## ZADANIE
Podepnij wszystkie triggery emailowe do gotowego modułu Notifications — sprawdź i uzupełnij brakujące szablony i wywołania.

## PLIKI DO PRZECZYTANIA
- backend/Modules/Vouchify.Modules.Notifications/
- backend/Modules/Vouchify.Modules.Orders/
- backend/Modules/Vouchify.Modules.Vouchers/
- backend/Modules/Vouchify.Modules.Tenants/

## CO ZROBIĆ
1. Zweryfikuj istnienie szablonów RazorLight dla każdego emaila — stwórz brakujące:
   - `OrderConfirmation.cshtml` — trigger: OrderPaid
   - `VoucherPdf.cshtml` — trigger: VoucherPdfGenerated (PDF jako załącznik)
   - `VoucherExpiryReminder.cshtml` — trigger: Hangfire job (7 dni przed)
   - `MonthlySalesSummary.cshtml` — trigger: Hangfire job (1. miesiąca)
   - `StripeOnboardingReminder.cshtml` — trigger: Hangfire job (24h StripePending)
2. Podepnij handler `OrderPaid` → wywołanie `INotificationService.SendOrderConfirmationAsync`
3. Podepnij handler `VoucherPdfGenerated` → wywołanie `INotificationService.SendVoucherPdfAsync` (PDF jako attachment z PdfUrl)
4. Sprawdź czy Hangfire jobs (Task 15) poprawnie wywołują `INotificationService`
5. Dodaj globalną stopkę z regulaminem platformy do każdego szablonu
6. Przetestuj lokalnie wysyłkę każdego emaila przez Resend sandbox
7. Po zakończeniu wszystkich kroków — zaznacz wszystkie checkboxy w sekcji ## DEFINICJA UKOŃCZENIA w tym pliku na [x]

## PO WYKONANIU

cd ~/projects/vouchify-mono
git add backend/Modules/Vouchify.Modules.Notifications/
git commit -m "feat(notifications): all email triggers wired, templates complete"
git push
docker compose -f docker-compose.dev.yml up -d --build api worker


## DEFINICJA UKOŃCZENIA
- [x] Email potwierdzenia zakupu wysyłany po OrderPaid
- [x] Email z PDF wysyłany po VoucherPdfGenerated
- [x] Email przypomnienia wysyłany 7 dni przed wygaśnięciem
- [x] Email podsumowania miesięcznego wysyłany 1. dnia miesiąca
- [x] Email Stripe reminder wysyłany po 24h StripePending
- [x] Każdy email zawiera stopkę z regulaminem
## _STATUS
- stan: completed
- ukończony: 2026-04-12 11:10:30
