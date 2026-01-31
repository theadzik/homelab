FROM alpine:3.23.3

ARG USER_ID=1000
ARG GROUP_ID=1000

RUN apk add --no-cache \
    openssl \
    rclone \
    tar

RUN addgroup --gid $GROUP_ID --system vaultwarden && \
    adduser --uid $USER_ID --system --ingroup vaultwarden --disabled-password --gecos "" vaultwarden

COPY --chown=vaultwarden:vaultwarden --chmod=755 backup.sh /backup.sh
USER vaultwarden:vaultwarden

ENTRYPOINT ["/backup.sh"]
