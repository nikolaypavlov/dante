FROM ubuntu:24.04

# System dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# GitHub CLI (for git authentication)
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh

# Claude Code
RUN mkdir /tmp/claude-install && cd /tmp/claude-install \
    && curl -fsSL https://claude.ai/install.sh | bash \
    && rm -rf /tmp/claude-install

ENV PATH="/root/.local/bin:$PATH"

# uv (Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV UV_LINK_MODE=copy

# Python 3.13
RUN uv python install 3.13

# Git config with gh credential helper
COPY gitconfig /root/.gitconfig

WORKDIR /workspace
