# syntax=docker/dockerfile:1

## Build
FROM golang:1.19.3-buster AS build

WORKDIR /app

COPY go.mod ./
COPY go.sum ./
RUN go mod download

COPY *.go ./

RUN go build -o /mock-api

## Deploy
FROM gcr.io/distroless/base-debian10

WORKDIR /

COPY ./public ./public
COPY --from=build /mock-api /mock-api

EXPOSE 5010

USER nonroot:nonroot

ENTRYPOINT ["/mock-api"]
