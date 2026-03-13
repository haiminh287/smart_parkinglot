FROM golang:1.22-alpine AS builder
WORKDIR /app

COPY go.mod ./
# Generate go.sum if missing
RUN go mod download || true

COPY . .
RUN go mod tidy
RUN CGO_ENABLED=0 GOOS=linux go build -o /realtime ./cmd/server/main.go

FROM alpine:3.19
RUN apk --no-cache add ca-certificates

COPY --from=builder /realtime /realtime

EXPOSE 8006

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:8006/health/ || exit 1

CMD ["/realtime"]
