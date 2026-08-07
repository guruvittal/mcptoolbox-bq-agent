# Multi-stage Dockerfile for MCP Toolbox on Cloud Run
# Stage 1: Use alpine to prepare tools.yaml with 644 permissions
FROM alpine:3.21 AS builder
WORKDIR /app
COPY tools.yaml /app/tools.yaml
RUN chmod 644 /app/tools.yaml

# Stage 2: Final minimal distroless image
FROM us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:latest
WORKDIR /app
COPY --from=builder /app/tools.yaml /app/tools.yaml

EXPOSE 8080

ENTRYPOINT ["/toolbox"]
CMD ["--config=/app/tools.yaml", "--address=0.0.0.0", "--port=8080"]
