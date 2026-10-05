# PostgreSQL ва нашри бехатари Shop Inventory

## Сабаби хориҷ шудани аккаунт

Дар санҷиши 4 октябри 2026 `/api/health/` дар сервери ҳозира SQLite-ро дар `/tmp/db.sqlite3` нишон дод; `DATABASE_URL` насб нашуда буд. Файлҳои муваққатии Vercel базаи доимӣ нестанд. Ҳангоми иваз шудани instance ё redeploy аккаунт метавонад дигар ёфт нашавад ва API хатои 401 диҳад.

Коди нав дар Vercel бе PostgreSQL ва анбори доимии аксҳо оғоз намешавад. **Пеш аз merge/deploy танзимоти поёнро анҷом диҳед.** Ҳоло ин дастур омода шудааст; базаи беруна сохта нашудааст ва маълумоти production кӯчонда нашудааст.

## 1. PostgreSQL созед

Роҳи пешниҳодшуда барои Vercel: [Neon дар Vercel Marketplace](https://vercel.com/marketplace/neon/neon). Пеш аз интихоб шартҳо, маҳдудият ва нархи нақшаи ҷориро бинед.

1. Ба Vercel дароед, лоиҳаи backend `shop-becend`-ро кушоед ва аз Marketplace интегратсияи Neon-ро интихоб кунед. Ё дар Neon мустақилона project созед.
2. Базаи production ва минтақаи ба backend наздикро интихоб кунед. Барои preview база ё branch-и ҷудо истифода баред: preview набояд ба маълумоти воқеӣ нависад.
3. Аз панели **Connect** connection string-и PostgreSQL-ро гиред. Барои runtime-и serverless аз pooled connection-и провайдер истифода баред; параметрҳои TLS-и додаашро нигоҳ доред.
4. Дар backend → Settings → Environment Variables онро бо номи маҳз `DATABASE_URL` сабт кунед. Агар интегратсия танҳо `POSTGRES_URL` дода бошад, барнома ҳоло `DATABASE_URL`-ро мехонад: ҳамин номро низ танзим кунед.
5. Парол ё URL-и базаро ба GitHub, screenshot ё чат нафиристед. Барои Development, Preview ва Production пайвастҳои мувофиқро ҷудо танзим кунед.

Барои базаи дигар ҳам connection string-и стандартии PostgreSQL кор мекунад: `postgresql://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require`. Ин танҳо намуна аст.

## 2. Аксу файлҳоро доимӣ нигоҳ доред

Дар Cloudinary аккаунт/cloud-и худро омода карда, се қиматро танҳо дар environment-и backend гузоред:

- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`

Vercel диск барои нигоҳдории доимии upload-и Django надорад. PostgreSQL танҳо маълумоти база ва истиноди аксҳоро нигоҳ медорад; худи файлҳоро Cloudinary нигоҳ медорад. Аксҳои мавҷударо пеш аз кӯчиш нусха бардоред ва барои кӯчондани онҳо нақшаи ҷудо иҷро кунед; иваз кардани storage худ аз худ файлҳои пешинаро намекӯчонад.

## 3. Environment-и backend

| Ном | Қимат / маъно |
| --- | --- |
| `DEBUG` | `False` |
| `SECRET_KEY` | Қимати тасодуфии доимӣ, ҳадди ақал 50 аломат; ҳангоми ҳар deploy нав накунед |
| `DATABASE_URL` | Пайвасти PostgreSQL аз қадами 1 |
| `ALLOWED_HOSTS` | `shop-becend.vercel.app` ва домени худ, бе `https://` |
| `CORS_ALLOWED_ORIGINS` | URL-и пурраи frontend, масалан `https://YOUR-FRONTEND.vercel.app`, бе `/` дар охир |
| `CSRF_TRUSTED_ORIGINS` | URL-и frontend ва backend бо `https://` |
| `FRONTEND_URL` | URL-и frontend барои пайванди барқароркунии парол |
| се `CLOUDINARY_...` | Қиматҳои қадами 2 |

Барои сохтани SECRET_KEY дар компютери худ `python -c "import secrets; print(secrets.token_urlsafe(64))"` иҷро карда, натиҷаро мустақим дар environment сабт кунед. Натиҷаро commit накунед.

Барои фиристодани мактубҳои reset, `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` ва TLS/SSL-и мувофиқи SMTP-ро гузоред. Бе SMTP мактуб ба корбар намеравад; дар local танҳо ба console мебарояд. `EMAIL_USE_TLS` ва `EMAIL_USE_SSL`-ро ҳамзамон фаъол накунед.

## 4. Backup ва migration

Пеш аз иваз кардани production маълумоти мавҷударо backup кунед. Базаи `/tmp` байни instance-ҳо умумӣ нест; агар instance-и кӯҳна аллакай нест шуда бошад, маълумоти гумшударо аз он барқарор карда намешавад. Коди нав худкор маълумоти кӯҳнаро намекӯчонад.

Барои базаи нав, аз checkout-и ҳамин версия дар муҳити боэътимод:

1. `python -m pip install -r requirements.txt`
2. `.env.example`-ро ба `.env` нусха кунед. Дар `.env` пайвасти базаи мақсаднок ва дигар қиматҳоро маҳаллӣ гузоред; файл ignored аст. Барои migration метавонед direct connection-и провайдерро истифода баред. Аз интихоб шудани базаи дуруст бовар ҳосил кунед.
3. `python manage.py check`
4. `python manage.py migrate --plan` — нақшаи тағйиротро бинед.
5. `python manage.py migrate --noinput`
6. Агар admin лозим бошад: `python manage.py createsuperuser`.

Барои базаи кӯҳна аввал нусхаи онро дар базаи озмоишӣ барқарор карда, migration-ро дар он санҷед. Ҳисобҳои бо login/email-и якхела аз рӯи ҳарфҳои калон/хурд бояд бо соҳибонашон ислоҳ шаванд. Migration 0005 ҳангоми чунин ихтилоф ID-ҳоро нишон дода бозмеистад; аккаунтҳоро ҳазф ё якҷо намекунад.

Migration-и кӯҳнаи default admin дигар парол ё аккаунт намесозад. Агар он қаблан дар production иҷро шуда бошад, аккаунтҳои admin-ро тафтиш кунед ва пароли пешфарзро бо `python manage.py changepassword <username>` иваз кунед. Истифодабарандагони дорои token-и версияи кӯҳна метавонанд як бор аз нав login кунанд.

Migration дигар ҳангоми ҳар оғоз шудани WSGI худкор иҷро намешавад. Дар Vercel онро ҳамчун қадами назоратшавандаи release, пеш аз deploy, иҷро кунед. Дар Render start command migration-ро пеш аз gunicorn иҷро мекунад; backup ва санҷиши пешакӣ ҳамоно лозим аст.

## 5. Frontend ва санҷиши release

1. Дар environment-и frontend `VITE_API_URL=https://shop-becend.vercel.app` гузоред (бе `/api`). Барои preview backend-и preview-ро нишон диҳед.
2. Backend-ро бо env-и пурра deploy кунед; баъд frontend-ро. Тағйири env ба deployment-и нав татбиқ мешавад: [дастури Vercel](https://vercel.com/docs/environment-variables/managing-environment-variables).
3. `/api/health/` бояд HTTP 200, `status=ok`, `is_postgres=true`, `db_reachable=true` диҳад. HTTP 503 маънои дастнорас будани база дорад.
4. Дар муҳити озмоишӣ register/login кунед, саҳифаро reload кунед, вкладкаи дуюм кушоед, профил/номро тағйир диҳед. Аккаунт бояд боқӣ монад.
5. Мол илова кунед, фурӯш ва баргардонӣ иҷро кунед. Ҷустуҷӯ, бақия, фоида ва архивро муқоиса кунед; таърихи чек пас аз архив бояд боқӣ монад.
6. Бо SMTP-и танзимшуда reset-ро аз мактуб санҷед; пайванди истифодашуда дубора кор намекунад. Дар staging redeploy карда, боқӣ мондани аккаунт/мол/аксро санҷед.

Код ва автоматикӣ-тестҳо SQLite-ро барои local дастгирӣ мекунанд; CI инчунин PostgreSQL-ро месанҷад. Бе танзим ва санҷиши боло нашри production пурра анҷомшуда ҳисоб намешавад.

## Render

`render.yaml` PostgreSQL ва Cloudinary-ро ҳамчун environment-и дастӣ талаб мекунад; он база ё диски пулакӣ намесозад. Алтернатива — диски воқеан доимӣ бо `DATA_DIR` дар host-и мувофиқ. Танҳо навиштани `/var/data` бе mount маълумотро доимӣ намекунад. Барои Vercel ин алтернатива истифода намешавад.
