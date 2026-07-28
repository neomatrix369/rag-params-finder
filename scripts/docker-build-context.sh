#!/usr/bin/env bash
# Compatibility shim — prefer scripts/docker/docker-build-context.sh
# shellcheck source=scripts/docker/docker-build-context.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/docker/docker-build-context.sh"
