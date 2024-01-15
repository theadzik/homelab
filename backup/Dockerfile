FROM alpine:3.19

RUN apk add --no-cache --upgrade \
    sqlite \
    bash \
    openssl

RUN addgroup --gid 20001 --system nonroot && \
    adduser --uid 10001 --system --ingroup nonroot --disabled-password --no-create-home --gecos "" nonroot

COPY --chown=nonroot:nonroot vaultwarden.sh vaultwarden.sh
USER nonroot:nonroot
RUN chmod +x /vaultwarden.sh
ENTRYPOINT ["/vaultwarden.sh"]
