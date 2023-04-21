FROM python:3.10.8
COPY . .
RUN pip install -r requirements.txt
CMD python3 -m src.daemon