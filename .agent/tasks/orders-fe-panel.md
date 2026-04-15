## ZADANIE
Stwórz widok listy zamówień i szczegółów w panelu właściciela z możliwością zwrotu.

## PLIKI DO PRZECZYTANIA
- frontend/src/app/features/

## CO ZROBIĆ
1. Stwórz feature `orders` w `frontend/src/app/features/orders/`
2. Komponent `OrderListComponent` — tabela zamówień z kolumnami: Data, Kupujący, Typ vouchera, Kwota, Status, Akcje
3. Filtry: Status (dropdown), Data od/do (datepicker), Typ vouchera (dropdown)
4. Komponent `OrderDetailComponent` — routing `/panel/orders/:id` — szczegóły: dane kupującego, odbiorcy, vouchera, historii statusów
5. Przycisk „Zwróć" w szczegółach zamówienia (widoczny tylko dla statusu Paid) → dialog potwierdzenia → `POST /api/orders/{id}/refund` → odśwież status
6. Badge statusu z kolorami: Pending (szary), Paid (zielony), Failed (czerwony), Refunded (pomarańczowy)
7. Routing: `/panel/orders`
8. Po zakończeniu wszystkich kroków — zaznacz wszystkie checkboxy w sekcji ## DEFINICJA UKOŃCZENIA w tym pliku na [x]

## PO WYKONANIU

cd ~/projects/vouchify-mono
git add frontend/src/app/features/orders/
git commit -m "feat(orders-fe): order list, filters, detail, refund"
git push
docker compose -f docker-compose.dev.yml up -d --build frontend


## DEFINICJA UKOŃCZENIA
- [x] Lista zamówień ładuje się z API
- [x] Filtry działają
- [x] Szczegóły zamówienia wyświetlają kompletne dane
- [x] Zwrot działa i odświeża status
## _STATUS
- stan: completed
- ukończony: 2026-04-11 20:25:44
