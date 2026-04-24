web: python manage.py migrate --noinput && python manage.py collectstatic --noinput --clear && gunicorn config.wsgi:application -c config/gunicorn.conf.py
