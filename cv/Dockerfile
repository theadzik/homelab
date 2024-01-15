FROM ruby:3.3.0-bookworm AS builder

COPY . app
WORKDIR app

RUN gem install jekyll bundler
RUN bundle install
RUN bundle exec jekyll build

FROM nginxinc/nginx-unprivileged:1.25.3

COPY --from=builder "/app/_site" /usr/share/nginx/html
