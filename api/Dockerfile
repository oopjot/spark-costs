FROM python:3.11-alpine
ENV PYTHONBUFFERED 1
RUN set -e;

RUN apk add --no-cache libpq-dev libffi-dev && \
    rm -rf /var/cache/apk/*

WORKDIR /opt/app

ADD pyproject.toml poetry.lock ./

RUN python3 -m pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--reload"]
