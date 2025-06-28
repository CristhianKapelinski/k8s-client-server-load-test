# Dockerfile.client.go
FROM golang:1.22-alpine as builder
WORKDIR /app
COPY client.go .
RUN go mod init mymodule || true # Initialize go module if not exists
RUN go build -o client .

FROM alpine:latest
WORKDIR /app
COPY --from=builder /app/client .
CMD ["./client"]