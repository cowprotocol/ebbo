FROM python:3.13-slim
COPY requirements.txt .
RUN python -m pip install -r requirements.txt
COPY . .

ENTRYPOINT [ "python", "-m", "src.daemon" ]
