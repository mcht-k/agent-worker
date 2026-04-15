## ZADANIE
Stwórz publiczną stronę oferty tenanta /t/:slug — mobile-first, bez autoryzacji.

## PLIKI DO PRZECZYTANIA
- frontend/src/app/features/
- frontend/src/app/app.routes.ts

## CO ZROBIĆ
1. Stwórz feature `storefront` w `frontend/src/app/features/storefront/`
2. Komponent `StorefrontPageComponent` — routing `/t/:slug`, lazy loaded, bez auth guard
3. Pobierz dane tenanta i vouchery: `GET /t/{slug}/vouchers` — wyświetl logo, nazwę, opis biznesu
4. Komponent `VoucherCardComponent` — karta vouchera z nazwą, opisem, ceną/wartością i przyciskiem „Kup teraz"
5. Layout mobile-first: max-width 480px na mobile, 720px na desktop, karty w kolumnie
6. Obsługa stanów: loading skeleton, błąd 404 (tenant nie istnieje), błąd 403 (tenant nieaktywny) z odpowiednimi komunikatami
7. Kliknięcie „Kup teraz" → przekierowanie do `/t/:slug/buy/:voucherTypeId` (routing do Orders FE — Task 11)
8. Po zakończeniu wszystkich kroków — zaznacz wszystkie checkboxy w sekcji ## DEFINICJA UKOŃCZENIA w tym pliku na [x]

## PO WYKONANIU

cd ~/projects/vouchify-mono
git add frontend/src/app/features/storefront/
git commit -m "feat(catalog-fe): public storefront page mobile-first"
git push
docker compose -f docker-compose.dev.yml up -d --build frontend


## DEFINICJA UKOŃCZENIA
- [x] Strona ładuje się pod `https://dev.vouchify.mtlabs.pl/t/{slug}`
- [x] Logo, nazwa, opis i lista voucherów wyświetlają się poprawnie
- [x] Stany błędów 404 i 403 obsłużone
- [x] Layout poprawny na mobile (375px)
## _STATUS
- stan: completed
- ukończony: 2026-04-11 20:25:29
