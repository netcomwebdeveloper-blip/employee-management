web: python manage.py migrate && python manage.py init_production_data && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
