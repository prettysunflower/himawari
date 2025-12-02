FROM alpine:3.22

RUN apk add curl python3
RUN adduser -D pixivnotifs

USER pixivnotifs

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/pixivnotifs/.local/bin/:$PATH"

WORKDIR /pixivnotifs

COPY --chown=1000:1000 . .

RUN uv sync

ENTRYPOINT ["uv", "run", "main.py"]