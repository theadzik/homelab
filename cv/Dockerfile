FROM ruby:latest AS builder

COPY . app
WORKDIR app

RUN gem install jekyll bundler
RUN bundle install
RUN bundle exec jekyll build

FROM --platform="linux/arm64" nginxinc/nginx-unprivileged:latest

COPY --from=builder "/app/_site" /usr/share/nginx/html
