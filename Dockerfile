FROM python:3.11
COPY requirements.txt .
RUN python -m pip install -r requirements.txt
COPY . .
CMD python -m src.daemon
