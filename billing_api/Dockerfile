FROM python:3.11

WORKDIR billing_api/src

COPY requirements.txt /billing_api/requirements.txt

RUN pip install --no-cache-dir -r /billing_api/requirements.txt

COPY src /billing_api/src

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
