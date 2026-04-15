## ZADANIE
Stwórz widok zarządzania typami voucherów w panelu Angular właściciela.

## PLIKI DO PRZECZYTANIA
- frontend/src/app/features/
- frontend/src/app/shared/

## CO ZROBIĆ
1. Stwórz feature `catalog` w `frontend/src/app/features/catalog/`
2. Komponent `VoucherTypeListComponent` — lista kart voucherów z drag & drop (Angular CDK) do zmiany kolejności → `PUT /api/catalog/voucher-types/reorder`, toggle widoczności → `PATCH .../visibility`, przycisk usuń z potwierdzeniem
3. Komponent `VoucherTypeFormComponent` — formularz tworzenia/edycji z zakładkami: (a) Podstawowe info, (b) Konfiguracja wartości, (c) Konfiguracja PDF
4. Zakładka konfiguracji wartości: radio Amount/Product, dla Amount — radio FixedList/FreeAmount/Slider z odpowiednimi polami, dla Product — pola nazwa/opis/zdjęcie/cena
5. Zakładka PDF: dropdown szablonu (1–5 z podglądem nazwy), checkboxy pól widoczności
6. Informacja o limicie voucherów (np. „3/10 typów voucherów")
7. Routing: `/panel/catalog`
8. Po zakończeniu wszystkich kroków — zaznacz wszystkie checkboxy w sekcji ## DEFINICJA UKOŃCZENIA w tym pliku na [x]

## PO WYKONANIU

cd ~/projects/vouchify-mono
git add frontend/src/app/features/catalog/
git commit -m "feat(catalog-fe): voucher type list, drag&drop, form with tabs"
git push
docker compose -f docker-compose.dev.yml up -d --build frontend


## DEFINICJA UKOŃCZENIA
- [x] Lista voucherów ładuje się z API
- [x] Drag & drop zapisuje nową kolejność
- [x] Formularz tworzy i edytuje vouchery obu typów
- [x] Konfiguracja PDF zapisuje się poprawnie
## _STATUS
- stan: completed
- ukończony: 2026-04-11 15:51:26
