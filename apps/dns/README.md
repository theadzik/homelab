# Building

```bash
APP_VERSION=2024.04.2
docker buildx build . \
  --no-cache \
  --build-arg APP_VERSION=$APP_VERSION \
  -t theadzik/dnsupdater:latest \
  -t theadzik/dnsupdater:$APP_VERSION \
  --platform=linux/arm64,linux/amd64 \
  --push
```
