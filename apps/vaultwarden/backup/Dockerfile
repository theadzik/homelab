FROM alpine:3.21

RUN apk add --no-cache --upgrade \
    sqlite \
    bash \
    openssl \
    rclone

RUN addgroup --gid 20001 --system vaultwarden && \
    adduser --uid 10001 --system --ingroup vaultwarden --disabled-password --gecos "" vaultwarden

COPY --chown=vaultwarden:vaultwarden --chmod=774 backup.sh backup.sh
USER vaultwarden:vaultwarden
ENTRYPOINT ["/backup.sh"]
