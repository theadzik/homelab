FROM alpine:3.23.3

ARG USER_ID=1000
ARG GROUP_ID=1000

RUN apk add --no-cache --upgrade \
    openssl \
    rclone

RUN addgroup --gid $GROUP_ID --system vaultwarden && \
    adduser --uid $USER_ID --system --ingroup vaultwarden --disabled-password --gecos "" vaultwarden

COPY --chown=$USER_ID:$GROUP_ID --chmod=774 restore.sh /restore.sh
USER $USER_ID:$GROUP_ID
ENTRYPOINT ["/restore.sh"]
