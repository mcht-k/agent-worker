## ZADANIE
Dodaj obsługę CORS preflight (OPTIONS) w konfiguracji Nginx dla Vouchify dev.
Plik do edycji: /opt/nginx/conf.d/vouchify-dev.conf

## PROBLEM
Przeglądarka wysyła preflight OPTIONS request który dostaje 502 zanim dotrze do API.

## CO ZROBIĆ

### 1. Odczytaj aktualny plik
cat /opt/nginx/conf.d/vouchify-dev.conf

### 2. Zaktualizuj blok `server` dla api.dev.vouchify.mtlabs.pl
Dodaj obsługę OPTIONS oraz nagłówki CORS w location /:

```nginx
location / {
    if ($request_method = 'OPTIONS') {
        add_header 'Access-Control-Allow-Origin' $http_origin always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, PATCH, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, Accept' always;
        add_header 'Access-Control-Allow-Credentials' 'true' always;
        add_header 'Content-Length' 0;
        return 204;
    }
    resolver 127.0.0.11 valid=30s;
    set $upstream http://vouchify_api_dev:5200;
    proxy_pass $upstream;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### 3. Przetestuj i przeładuj Nginx
docker exec nginx-proxy nginx -t && docker exec nginx-proxy nginx -s reload

### 4. Weryfikacja
curl -s -o /dev/null -w "%{http_code}" -X OPTIONS https://api.dev.vouchify.mtlabs.pl/api/identity/login 
-H "Origin: https://dev.vouchify.mtlabs.pl" 
-H "Access-Control-Request-Method: POST"
Powinno zwrócić 204.

### 5. Po zakończeniu wszystkich kroków — zaznacz wszystkie checkboxy w sekcji ## STATUS w tym pliku na [x]

## WAŻNE
- Nie modyfikuj żadnych innych plików w /opt/nginx/conf.d/
- Nie restartuj nginx-proxy, tylko nginx -s reload

## STATUS
- [x] vouchify-dev.conf zaktualizowany
- [x] nginx -t OK
- [x] curl OPTIONS zwraca 204

## _STATUS
- stan: completed
- ukończony: 2026-04-11 00:00:00
- notatka: ukończono przed wdrożeniem systemu kolejki
