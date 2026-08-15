FROM rclone/rclone:1.75.0 AS rclone

FROM dhi.io/alpine-base:3.24-dev AS build

RUN apk add --no-cache \
    openssl \
    tar \
    sqlite

# sqlite3 and tar below are invisible to every scanner we run, and to the SBOM.
#
# They arrive by COPY, so the final image has no apk record of them, and nothing
# in the scan classifies either from the binary alone. What coverage there is
# comes from somewhere else: the openssl libraries because the base image's apk
# database records libcrypto3 and libssl3, and rclone because Go binaries embed
# their module list. Measured against the published image: 253 components, 7 apk
# packages and 246 Go modules read out of /usr/bin/rclone, with sqlite3 3.53.2
# and GNU tar 1.35 both running and appearing in neither.
#
# A CVE in either would therefore not fail the build gate and would not show up
# in the daily scan. Three fixes were tried and rejected: the non-dev dhi base
# ships no apk, so they cannot be installed in the final stage; copying the build
# stage's apk database would claim the dev toolchain is present too; and
# BUILDKIT_SBOM_SCAN_STAGE does not apply, because the SBOM is written by Trivy
# from the built layout rather than by BuildKit.
#
# So this is an accepted gap. If you add another copied binary, add it here.
FROM dhi.io/alpine-base:3.24

COPY --from=build /usr/lib/ /usr/lib/
COPY --from=build /usr/bin/openssl /usr/bin/openssl
COPY --from=build /bin/tar /usr/bin/tar
COPY --from=build /usr/bin/sqlite3 /usr/bin/sqlite3
COPY --from=rclone /usr/local/bin/rclone /usr/bin/rclone

COPY --chown=nonroot:nonroot --chmod=755 restore.sh /restore.sh
USER nonroot
ENTRYPOINT ["/restore.sh"]
