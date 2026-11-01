FROM python:3.15.0-slim-bookworm@sha256:0e019bbdfb5d9874cb2389f1c2884b64aa2ac97c99960b5bc521cef978c0617d AS base

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
