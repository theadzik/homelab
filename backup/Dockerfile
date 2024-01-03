FROM --platform="linux/arm64" alpine:3.19

RUN apk add --no-cache --upgrade \
    sqlite \
    bash \
    openssl

RUN addgroup --gid 20001 --system nonroot && \
    adduser --uid 10001 --system --ingroup nonroot --disabled-password --no-create-home --gecos "" nonroot

COPY --chown=nonroot:nonroot vaultwarden.sh vaultwarden.sh
USER nonroot:nonroot

ENTRYPOINT ["sh", "vaultwarden.sh"]
