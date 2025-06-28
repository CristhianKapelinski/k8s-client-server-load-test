# Dockerfile.server.go
FROM golang:1.22-alpine as builder
WORKDIR /app
COPY server.go .
RUN go mod init mymodule || true # Initialize go module if not exists
RUN go build -o server .

FROM alpine:latest
WORKDIR /app
COPY --from=builder /app/server .
EXPOSE 8080
CMD ["./server"]