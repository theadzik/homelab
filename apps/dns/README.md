# Building

```bash
APP_VERSION=3.2.0
docker build . --build-arg APP_VERSION=$APP_VERSION \
  -t theadzik/dnsupdater:latest -t theadzik/dnsupdater:$APP_VERSION \
  --platform=linux/arm64
docker push theadzik/dnsupdater:$APP_VERSION
docker push theadzik/dnsupdater:latest
```
