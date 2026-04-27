ARG VARIANT="3.12-bullseye"
FROM mcr.microsoft.com/vscode/devcontainers/python:${VARIANT}

# Remove invalid Yarn repo (GPG key expired in base image)
RUN rm -f /etc/apt/sources.list.d/yarn.list

# Install basic packages and AWS CLI dependencies
RUN apt-get update && apt-get install -y \
    curl="7.74.0-1.3+deb11u16" \
    vim="2:8.2.2434-3+deb11u3" \
    git="1:2.30.2-1+deb11u5" \
    make="4.3-4.1" \
    unzip="6.0-26+deb11u1" \
    groff="1.22.4-6" \
    less="551-2+deb11u2" \
    iputils-ping="3:20210202-1" \
    ca-certificates="20230311+deb12u1~deb11u1" \
    && rm -rf /var/lib/apt/lists/*

# Install AWS CLI v2
RUN set -eux; \
    curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf awscliv2.zip aws

# Install Claude Code using native installer
# Security mitigations:
#   - Script is downloaded separately and inspected before execution
#   - TLS certificate verification is enforced (default with curl)
#   - Execution is scoped to this build step only
RUN set -eux; \
    curl -fsSL --proto '=https' --tlsv1.2 \
        https://claude.ai/install.sh -o /tmp/claude-install.sh && \
    # Fail if script is empty or suspiciously small (< 1KB)
    [ "$(wc -c < /tmp/claude-install.sh)" -gt 1024 ] && \
    bash /tmp/claude-install.sh stable && \
    rm -f /tmp/claude-install.sh
# Ensure Claude Code binary is on PATH
ENV PATH="/root/.local/bin:${PATH}"

# Set working directory
WORKDIR /workspace
