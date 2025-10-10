FROM alpine:3.22.2

ARG USER_ID=10001
ARG GROUP_ID=20001

RUN apk add --no-cache --upgrade \
    bash \
    openssl \
    rclone

RUN addgroup --gid $GROUP_ID --system vaultwarden && \
    adduser --uid $USER_ID --system --ingroup vaultwarden --disabled-password --gecos "" vaultwarden

COPY --chown=$USER_ID:$GROUP_ID --chmod=774 restore.sh /restore.sh
USER $USER_ID:$GROUP_ID
ENTRYPOINT ["/restore.sh"]
