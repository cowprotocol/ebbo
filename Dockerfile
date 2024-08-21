FROM python:3.12
COPY requirements.txt .
RUN python -m pip install -r requirements.txt
COPY . .
CMD python -m src.daemon
