FROM alpine:3.23.2

ARG USER_ID=10001
ARG GROUP_ID=20001

RUN apk add --no-cache --upgrade \
    sqlite \
    openssl \
    rclone

RUN addgroup --gid $GROUP_ID --system vaultwarden && \
    adduser --uid $USER_ID --system --ingroup vaultwarden --disabled-password --gecos "" vaultwarden

COPY --chown=vaultwarden:vaultwarden --chmod=774 backup.sh /backup.sh
USER $USER_ID:$GROUP_ID
ENTRYPOINT ["/backup.sh"]
