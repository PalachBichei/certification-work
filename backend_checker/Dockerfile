FROM python:3.10

WORKDIR /opt/app

COPY ./src /opt/app/src
COPY requirements.txt /opt/app/


RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

WORKDIR /opt/app/src


# uvicorn main:app --host 0.0.0.0 --port 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]