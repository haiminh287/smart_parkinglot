FROM golang:1.22-alpine AS builder
WORKDIR /app

COPY go.mod ./
# Generate go.sum if missing (go mod tidy needs source for import analysis)
RUN go mod download || true

COPY . .
RUN go mod tidy
RUN CGO_ENABLED=0 GOOS=linux go build -o /gateway ./cmd/server/main.go

FROM alpine:3.19
RUN apk --no-cache add ca-certificates

COPY --from=builder /gateway /gateway

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:8000/health/ || exit 1

CMD ["/gateway"]
