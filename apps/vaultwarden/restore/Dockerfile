FROM alpine:3.23.3

ARG USER_ID=1000
ARG GROUP_ID=1000

RUN apk add --no-cache \
    openssl \
    rclone \
    tar \
    sqlite

RUN addgroup --gid $GROUP_ID --system vaultwarden && \
    adduser --uid $USER_ID --system --ingroup vaultwarden --disabled-password --gecos "" vaultwarden

COPY --chown=vaultwarden:vaultwarden --chmod=755 restore.sh /restore.sh
USER vaultwarden:vaultwarden

ENTRYPOINT ["/restore.sh"]
