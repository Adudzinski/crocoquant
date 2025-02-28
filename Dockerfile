FROM python:3.10.12
WORKDIR /app
COPY . .
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt
CMD ["python", "bot.py"]

