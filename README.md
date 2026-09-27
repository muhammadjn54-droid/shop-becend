# Shop Inventory API

Backend на Django + Django REST Framework для учёта товаров, склада и продаж.
Swagger, JWT-авторизация, атомарные продажи, статистика и дашборд.

## 1. Структура проекта

```
shop_backend/
├── manage.py
├── requirements.txt
├── .gitignore
├── shop_backend/          # настройки проекта
│   ├── settings.py
│   ├── urls.py            # + Swagger/Redoc + media
│   ├── wsgi.py
│   └── asgi.py
├── accounts/               # регистрация, вход, JWT
│   ├── models.py           # CustomUser
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   └── tests.py
├── products/                # товары, склад, статистика, дашборд
│   ├── models.py             # Product + вычисляемые свойства
│   ├── serializers.py
│   ├── views.py              # CRUD, sell, add-stock, return, low-stock, statistics, dashboard
│   ├── urls.py
│   ├── admin.py
│   └── tests.py
├── sales/                    # продажи
│   ├── models.py             # Sale
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   └── tests.py
└── media/                    # сюда сохраняются загруженные фото товаров
```

## 2. Запуск проекта

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt

python manage.py makemigrations
python manage.py migrate

python manage.py createsuperuser

python manage.py runserver
```

Swagger UI: http://127.0.0.1:8000/swagger/
Redoc:      http://127.0.0.1:8000/redoc/
Admin:      http://127.0.0.1:8000/admin/

По умолчанию используется SQLite (файл `db.sqlite3`, создаётся автоматически).
Чтобы переключиться на PostgreSQL — раскомментируйте блок `DATABASES` в
`shop_backend/settings.py` и задайте переменные окружения `DB_NAME`,
`DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`.

Запуск тестов:

```bash
python manage.py test
```

## 3. Авторизация

Все endpoint'ы товаров и продаж требуют авторизации через JWT.

1. Зарегистрируйтесь: `POST /api/auth/register/` — в ответе сразу придут `access` и `refresh` токены.
2. Либо войдите: `POST /api/auth/login/`.
3. Каждый запрос отправляйте с заголовком:

```
Authorization: Bearer <access_token>
```

В Swagger нажмите кнопку **Authorize** и введите `Bearer <ваш_access_token>`.

Каждый пользователь видит и может изменять только свои товары и продажи.

### Auth endpoints

| Метод | URL | Описание |
|---|---|---|
| POST | `/api/auth/register/` | Регистрация (`username`, `email`, `password`, `password2`) |
| POST | `/api/auth/login/` | Вход (`username`, `password`) → `access`, `refresh` |
| POST | `/api/auth/token/refresh/` | Обновить `access` токен по `refresh` |
| GET  | `/api/auth/me/` | Текущий пользователь |
| POST | `/api/auth/logout/` | Выход (`refresh` попадает в blacklist) |

## 4. Товары (Products)

| Метод | URL | Описание |
|---|---|---|
| GET | `/api/products/` | Список товаров (поиск `?search=`, сортировка `?ordering=`, фильтр по `arrival_date`/`name`) |
| POST | `/api/products/` | Создать товар (multipart/form-data, можно с фото) |
| GET | `/api/products/{id}/` | Один товар |
| PUT/PATCH | `/api/products/{id}/` | Изменить товар |
| DELETE | `/api/products/{id}/` | Удалить товар |
| GET | `/api/products/low-stock/` | Товары с остатком ≤ 5 |
| POST | `/api/products/{id}/sell/` | Продать товар |
| POST | `/api/products/{id}/add-stock/` | Зарегистрировать новую партию |
| POST | `/api/products/{id}/return/` | Оформить возврат |
| GET | `/api/products/{id}/sales/` | История продаж товара |

## 5. Продажи (Sales)

| Метод | URL | Описание |
|---|---|---|
| GET | `/api/sales/` | Все продажи текущего пользователя |
| GET | `/api/sales/{id}/` | Одна продажа |

## 6. Статистика

| Метод | URL | Описание |
|---|---|---|
| GET | `/api/statistics/` | Общая статистика магазина |
| GET | `/api/dashboard/` | Сводная панель + последние продажи + топ-5 товаров |

## 7. Формулы простыми словами

**Остаток товара**
```
remaining_quantity = quantity_received - quantity_sold
```
Сколько единиц товара физически лежит на складе прямо сейчас: сколько пришло минус сколько уже продано.

**Выручка**
```
revenue = quantity_sold * selling_price
```
Сколько денег покупатели заплатили за проданный товар.

**Себестоимость проданного товара**
```
sold_cost = quantity_sold * purchase_price
```
Во сколько магазину обошлась закупка того количества товара, которое уже продано.

**Прибыль**
```
profit = revenue - sold_cost, если revenue > sold_cost, иначе 0
```
Разница между тем, что получили от продажи, и тем, что потратили на закупку. Если продали дороже, чем купили — это прибыль.

**Убыток**
```
loss = sold_cost - revenue, если sold_cost > revenue, иначе 0
```
Обратная ситуация: продали дешевле, чем купили — разница считается убытком.

**Прибыль/убыток с одной единицы товара**
```
profit_per_item = selling_price - purchase_price
```
Показывает маржу на одну единицу товара — положительное число означает прибыль с каждой проданной штуки, отрицательное — убыток.

## 8. Пример полного цикла запросов

```bash
# 1. Регистрация
curl -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username":"shopowner","password":"Str0ngPass!123","password2":"Str0ngPass!123"}'
# → в ответе: access, refresh

# 2. Создание товара (с фото)
curl -X POST http://127.0.0.1:8000/api/products/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F "name=Coca-Cola" \
  -F "arrival_date=2026-09-27" \
  -F "quantity_received=20" \
  -F "purchase_price=8" \
  -F "selling_price=10" \
  -F "image=@cola.png"

# 3. Продажа 3 штук
curl -X POST http://127.0.0.1:8000/api/products/1/sell/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"quantity": 3}'
# → remaining_quantity: 17, revenue: 30, sold_cost: 24, profit: 6, loss: 0

# 4. Поступление новой партии
curl -X POST http://127.0.0.1:8000/api/products/1/add-stock/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"quantity": 10}'

# 5. Возврат товара
curl -X POST http://127.0.0.1:8000/api/products/1/return/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"quantity": 1}'

# 6. Статистика магазина
curl http://127.0.0.1:8000/api/statistics/ -H "Authorization: Bearer <ACCESS_TOKEN>"

# 7. Дашборд
curl http://127.0.0.1:8000/api/dashboard/ -H "Authorization: Bearer <ACCESS_TOKEN>"
```

## 9. Что уже проверено

Проект был протестирован вживую в процессе разработки:
- регистрация и вход возвращают рабочие JWT токены;
- создание товара через multipart/form-data с реальным файлом изображения;
- изображение действительно сохраняется и доступно по `/media/...`;
- продажа корректно уменьшает остаток и рассчитывает прибыль/убыток;
- попытка продать больше, чем есть на складе, возвращает 400 с понятным сообщением;
- `/api/statistics/` и `/api/dashboard/` возвращают верные агрегированные числа;
- 14 автотестов (`python manage.py test`) проходят успешно.
