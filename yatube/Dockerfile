FROM python:3.7-slim

WORKDIR /app

COPY requirements.txt .

RUN python3 -m pip install --upgrade pip && \
    pip3 install -r requirements.txt --no-cache-dir

COPY . .

CMD ["gunicorn", "yatube.wsgi:application", "--bind", "127.0.0.1:8001" ]