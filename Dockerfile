FROM ubuntu:22.04

RUN apt-get update && \
    apt-get install -y curl && \
    apt-get install -y python3 python3-pip

RUN apt-get install -y git

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

RUN rm -rf /var/lib/apt/lists/*

RUN mkdir /app

WORKDIR /app

ENV PATH="/root/.local/bin/env:${PATH}"

RUN git clone https://github.com/cnitlrt/ChatBridge && cd ChatBridge && git submodule update --init --recursive && /root/.local/bin/uv venv --python 3.12 && /root/.local/bin/uv pip install -e . && /root/.local/bin/uv pip install -r ./Turnstile-Solver/requirements.txt

RUN cd ChatBridge/Turnstile-Solver && /root/.local/bin/uv run -m camoufox fetch

ENTRYPOINT ["/bin/bash"]