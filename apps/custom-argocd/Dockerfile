FROM quay.io/argoproj/argocd:latest

# Switch to root for the ability to perform install
USER root

RUN apt-get update && \
    apt-get install --no-install-recommends -y \
        git-crypt && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN mv /usr/bin/git /usr/bin/git.bin
COPY --chmod=755 git /usr/bin/git

# Switch back to non-root user
USER $ARGOCD_USER_ID
