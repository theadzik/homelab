ARG TAG="latest"
FROM ubuntu:24.04 AS downloader
ARG GIT_CRYPT_VERSION="0.8.0"
ARG GIT_CRYPT_SHA265="522683f89693ad2da1f3fa7e1076f5e8934619a55ff2e1246866eeb2ad587b0c"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update && apt-get install -y wget ca-certificates --no-install-recommends && \
    wget -nv "https://github.com/AGWA/git-crypt/releases/download/$GIT_CRYPT_VERSION/git-crypt-$GIT_CRYPT_VERSION-linux-x86_64" -O /git-crypt && \
    echo "$GIT_CRYPT_SHA265 /git-crypt" | sha256sum -c -

FROM quay.io/argoproj/argocd:${TAG}

# Switch to root for the ability to perform install
USER root

COPY --chmod=755 --from=downloader /git-crypt /usr/local/bin/git-crypt

RUN mv /usr/bin/git /usr/bin/git.bin
COPY --chmod=755 git /usr/bin/git

# Switch back to non-root user
USER $ARGOCD_USER_ID
