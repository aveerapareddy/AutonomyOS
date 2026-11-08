#!/usr/bin/env bash
# Official Ubuntu packages for the disposable Ubuntu 24.04 validation image.
# Run as root inside the pod, never on a personal host. No kernel driver installation.
set -euo pipefail
if [[ "$(id -u)" != 0 ]]; then echo 'Run inside the disposable GPU container as root.' >&2; exit 1; fi
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends libxt6 libxrandr2 libxinerama1 libxcursor1 libxi6 libglu1-mesa libegl1 libgl1 libglx0 vulkan-tools
vulkaninfo --summary
