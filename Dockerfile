FROM python:3.12-slim

# 1) system libs for pandas/TA; remove if you genuinely don't need them
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc build-essential ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2) keep the big cache layer: install deps first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3) now copy project sources; edits here won't bust the pip cache
COPY . .

ENTRYPOINT ["python", "-u", "bot.py"]



