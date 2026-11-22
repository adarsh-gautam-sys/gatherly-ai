FROM python:3.15.2-slim-bookworm@sha256:96599df822d0e1c6bb700014a05c7f3c8cabc6e0f7ff3c4f9f69cee033b4b5d9 AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

FROM base AS build
WORKDIR /build
COPY requirements.txt pyproject.toml README.md LICENSE ./
COPY src/ src/
COPY prompts/ prompts/
RUN python -m pip install --no-cache-dir -c requirements.txt pip hatchling editables \
    && python -m pip wheel --no-cache-dir --no-build-isolation -c requirements.txt -w /wheels . \
    && python -m venv --without-pip /opt/venv \
    && python -m pip --python /opt/venv install --no-index --find-links=/wheels /wheels/gatherly_ai-*.whl

FROM base AS runtime
COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /app
USER 10001:10001
EXPOSE 8080
CMD ["python", "-m", "gatherly.serve"]
