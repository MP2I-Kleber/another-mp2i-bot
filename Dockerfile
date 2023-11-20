FROM python:3.12 as base
RUN apt-get update && apt-get install -y poppler-utils
WORKDIR /app
ENV PYTHONUNBUFFERED=0
COPY ./requirements.txt /app
RUN pip install -r requirements.txt

FROM base as prod
COPY ./src ./
CMD ["python", "./main.py"]

FROM base as debug
ENV DEBUG=1
ENV LOG_LEVEL=DEBUG
RUN pip install debugpy
CMD ["python", "-m", "debugpy", "--wait-for-client", "--listen", "0.0.0.0:5678", "./main.py"]
# CMD ["python", "./main.py"]
