#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
SERVICE_NAME="${SERVICE_NAME:-app}"
HEALTH_RETRIES="${HEALTH_RETRIES:-20}"
HEALTH_DELAY="${HEALTH_DELAY:-3}"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required to run this script" >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required to run this script" >&2
  exit 1
fi

cleanup() {
  docker compose -f "${COMPOSE_FILE}" down --remove-orphans >/dev/null
}
trap cleanup EXIT

echo "Building container image..."
docker compose -f "${COMPOSE_FILE}" build

echo "Starting stack..."
docker compose -f "${COMPOSE_FILE}" up -d

container_id="$(docker compose -f "${COMPOSE_FILE}" ps -q "${SERVICE_NAME}")"
if [[ -z "${container_id}" ]]; then
  echo "failed to resolve container id for service ${SERVICE_NAME}" >&2
  exit 1
fi

echo "Waiting for health status..."
for attempt in $(seq 1 "${HEALTH_RETRIES}"); do
  status="$(docker inspect --format '{{.State.Health.Status}}' "${container_id}")"
  if [[ "${status}" == "healthy" ]]; then
    break
  fi
  if [[ "${attempt}" -eq "${HEALTH_RETRIES}" ]]; then
    echo "container failed to become healthy (last status: ${status})" >&2
    docker logs "${container_id}" >&2 || true
    exit 1
  fi
  sleep "${HEALTH_DELAY}"
done

uid="$(docker exec "${container_id}" id -u)"
if [[ "${uid}" -eq 0 ]]; then
  echo "container user must not be root" >&2
  exit 1
fi

port="${IDEA_API_PORT:-8000}"
echo "Checking external /health endpoint on localhost:${port}..."
curl -fsS "http://localhost:${port}/health" >/dev/null

echo "Containers look healthy and run as uid ${uid}."
