FROM python:3.12-slim
WORKDIR /app
COPY backend/app/ /app/backend/app/
COPY jobs/run_gate_batch.py /app/jobs/run_gate_batch.py
COPY data/workmanship-rules.v0.json /app/data/workmanship-rules.v0.json
ENV PYTHONPATH=/app/backend
ENTRYPOINT ["python", "/app/jobs/run_gate_batch.py"]
