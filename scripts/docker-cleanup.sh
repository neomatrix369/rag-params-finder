#!/usr/bin/env bash
# Compatibility shim — prefer scripts/docker/docker-cleanup.sh
# shellcheck source=scripts/docker/docker-cleanup.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/docker/docker-cleanup.sh"
