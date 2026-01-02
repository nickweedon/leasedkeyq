FROM python:3.12-slim-bookworm

# Build arguments
ARG CREATE_VSCODE_USER=true

# Install system dependencies including make for build process
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    sudo \
    make \
    && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 and Claude Code CLI
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g @anthropic-ai/claude-code

# Install UV package manager for root
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Add UV to PATH for root
ENV PATH="/root/.cargo/bin:${PATH}"

# Install Python build tools globally (build, twine)
RUN pip install --no-cache-dir build twine

# Conditionally create vscode user
RUN if [ "$CREATE_VSCODE_USER" = "true" ]; then \
    groupadd --gid 1000 vscode && \
    useradd --uid 1000 --gid 1000 -m vscode && \
    echo "vscode ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    # Install UV for vscode user \
    su - vscode -c "curl -LsSf https://astral.sh/uv/install.sh | sh" && \
    # Add UV to vscode user's PATH via .bashrc \
    echo 'export PATH="/home/vscode/.local/bin:$PATH"' >> /home/vscode/.bashrc; \
    fi

# Add UV to PATH for all users (including vscode)
ENV PATH="/home/vscode/.local/bin:/root/.cargo/bin:${PATH}"

# Set working directory
WORKDIR /workspace

# Default command
CMD ["/bin/bash"]
