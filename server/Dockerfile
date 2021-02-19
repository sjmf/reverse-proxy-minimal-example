FROM python:3.8
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app

EXPOSE 5000

CMD ["gunicorn", "--log-file=-", "--bind=0.0.0.0:5000", "server:app"]
