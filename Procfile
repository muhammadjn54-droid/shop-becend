web: sh -c "python manage.py migrate --noinput && gunicorn shop_backend.wsgi:application --bind 0.0.0.0:$PORT --workers ${WEB_CONCURRENCY:-1} --threads ${WEB_THREADS:-4} --timeout 120"
