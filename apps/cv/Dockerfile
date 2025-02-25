FROM ruby:3.4-bookworm AS builder
ARG JEKYLL_ENV=production
RUN gem install jekyll:4.4.1 bundler:2.6.5

COPY Gemfile Gemfile.lock /app/
WORKDIR /app
RUN bundle install

COPY . /app/
RUN bundle exec jekyll build

FROM nginxinc/nginx-unprivileged:1.27-alpine3.21-slim

COPY --from=builder "/app/_site" /usr/share/nginx/html
