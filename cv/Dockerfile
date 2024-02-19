FROM ruby:3.3.0-bookworm AS builder

RUN gem install jekyll bundler

COPY . app
WORKDIR app

RUN bundle install && \
    bundle exec jekyll build

FROM nginxinc/nginx-unprivileged:alpine-slim

COPY --from=builder "/app/_site" /usr/share/nginx/html
