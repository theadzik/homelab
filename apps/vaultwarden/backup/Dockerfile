FROM dhi.io/alpine-base:3.24-dev AS build

RUN apk add --no-cache \
    openssl \
    rclone \
    tar \
    sqlite

FROM dhi.io/alpine-base:3.24

COPY --from=build /usr/lib/ /usr/lib/
COPY --from=build /usr/bin/openssl /usr/bin/openssl
COPY --from=build /usr/bin/rclone /usr/bin/rclone
COPY --from=build /usr/bin/tar /usr/bin/tar
COPY --from=build /usr/bin/sqlite3 /usr/bin/sqlite3

COPY --chown=nonroot:nonroot --chmod=755 backup.sh /backup.sh
USER nonroot
ENTRYPOINT ["/backup.sh"]
