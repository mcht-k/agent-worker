## ZADANIE
Stwórz widok zakupu vouchera na stronie publicznej: formularz danych, wybór wartości, redirect do Stripe.

## PLIKI DO PRZECZYTANIA
- frontend/src/app/features/storefront/

## CO ZROBIĆ
1. Stwórz komponent `BuyVoucherPageComponent` — routing `/t/:slug/buy/:voucherTypeId`, lazy loaded, bez auth guard
2. Krok 1 — wybór wartości:
   - Dla FixedList: przyciski z wartościami
   - Dla FreeAmount: pole numeryczne z walidacją min/max
   - Dla Slider: slider z etykietą aktualnej wartości
3. Krok 2 — formularz danych:
   - Pola: Twoje imię, Twój email
   - Checkbox „Kup jako prezent" → odkrywa pola: Imię odbiorcy, Email odbiorcy
4. Przycisk „Przejdź do płatności" → `POST /t/{slug}/orders/checkout` → redirect do `checkoutUrl`
5. Strona `/t/:slug/success` — potwierdzenie zakupu (komunikat + link powrotu do oferty)
6. Strona `/t/:slug/cancel` — anulowanie płatności (komunikat + link powrotu)
7. Obsługa błędów API: toast z komunikatem błędu
8. Po zakończeniu wszystkich kroków — zaznacz wszystkie checkboxy w sekcji ## DEFINICJA UKOŃCZENIA w tym pliku na [x]

## PO WYKONANIU

cd ~/projects/vouchify-mono
git add frontend/src/app/features/storefront/
git commit -m "feat(orders-fe): buy voucher flow, stripe redirect, success/cancel pages"
git push
docker compose -f docker-compose.dev.yml up -d --build frontend


## DEFINICJA UKOŃCZENIA
- [x] Wybór wartości działa dla wszystkich trybów (FixedList, FreeAmount, Slider)
- [x] Formularz waliduje wymagane pola
- [x] Redirect do Stripe Checkout działa
- [x] Strony success i cancel wyświetlają poprawne komunikaty
## _STATUS
- stan: completed
- ukończony: 2026-04-11 20:31:59
