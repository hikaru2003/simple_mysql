#!/bin/bash

# Setup script for simple_mysql experiment on CloudLab
# - Install CPU frequency utilities
# - Disable turbo boost and set performance governor
# - Clone simple_mysql repository (pre-built binary included)

INSTALL_PACKAGES="git python3 python3-pip python3-pandas cpufrequtils linux-tools-common linux-tools-generic zsh curl htop"
GIT_REPO_URL="https://github.com/hikaru2003/simple_mysql.git"
USER_HOME=/users/Morisaki

set -x
exec > >(tee -a /local/startup.log) 2>&1
echo "=== Startup script started ==="

# Disable Turbo Boost
echo "Disabling Turbo Boost..."
if [ -e /sys/devices/system/cpu/intel_pstate/no_turbo ]; then
    echo 1 > /sys/devices/system/cpu/intel_pstate/no_turbo
    echo "Intel turbo disabled."
elif [ -e /sys/devices/system/cpu/cpufreq/boost ]; then
    echo 0 > /sys/devices/system/cpu/cpufreq/boost
    echo "AMD boost disabled."
else
    echo "Turbo control not found, skipping."
fi

# Install packages
echo "Installing packages..."
DEBIAN_FRONTEND=noninteractive apt update
DEBIAN_FRONTEND=noninteractive apt install -y ${INSTALL_PACKAGES}

# Set performance governor
echo "Setting CPU governor to performance..."
cpupower frequency-set -g performance || echo "cpupower failed, trying cpufreq-set..."
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo performance > $cpu 2>/dev/null || true
done

# Clone simple_mysql repository (pre-built binary included)
echo "Cloning simple_mysql repository..."
cd $USER_HOME
git clone ${GIT_REPO_URL}
chmod +x $USER_HOME/simple_mysql/simple_lock $USER_HOME/simple_mysql/pause_cycle_count

# Change ownership
USER_NAME=Morisaki
USER_GROUP=sslabko-fast-nw-
chown -R $USER_NAME:$USER_GROUP $USER_HOME/simple_mysql

echo "=== Startup script completed ==="
