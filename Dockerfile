FROM python:3.12.16-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337 AS base

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
