FROM alpine:3.19

RUN apk add --no-cache --upgrade \
    sqlite \
    bash \
    openssl

RUN addgroup --gid 20001 --system vaultwarden && \
    adduser --uid 10001 --system --ingroup vaultwarden --disabled-password --no-create-home --gecos "" vaultwarden

COPY --chown=vaultwarden:vaultwarden vaultwarden.sh vaultwarden.sh
USER vaultwarden:vaultwarden
RUN chmod +x /vaultwarden.sh
ENTRYPOINT ["/vaultwarden.sh"]
