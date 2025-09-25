# Dockerfile in topic_skill_service_example
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PORT=5000
WORKDIR /app
COPY requirements.txt requirements.txt
RUN python -m pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt
COPY . .
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/entrypoint.sh && \
    chmod 755 /usr/local/bin/entrypoint.sh
EXPOSE 5000
ENTRYPOINT ["/bin/sh", "/usr/local/bin/entrypoint.sh"]