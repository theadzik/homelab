FROM ruby:3.3-bookworm AS builder

RUN gem install jekyll bundler

COPY Gemfile Gemfile.lock /app/
WORKDIR app
RUN bundle install

COPY . /app/
RUN bundle exec jekyll build

FROM nginxinc/nginx-unprivileged:alpine-slim

COPY --from=builder "/app/_site" /usr/share/nginx/html
