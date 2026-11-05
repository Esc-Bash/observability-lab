FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt constraints.txt ./
# constraints.txt pins the OpenTelemetry versions for every pip install below
ENV PIP_CONSTRAINT=/app/constraints.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
EXPOSE 8002
CMD ["python", "app.py"]
