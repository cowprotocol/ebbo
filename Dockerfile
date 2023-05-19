FROM python:3.11
COPY . .
RUN pip install -r requirements.txt
CMD python3.11 -m src.daemon