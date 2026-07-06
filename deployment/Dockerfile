FROM python:3.12.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /opt/amr-fleet

COPY pyproject.toml README.md LICENSE ./
COPY ros_ws/src/amr_fleet_core ./ros_ws/src/amr_fleet_core

RUN python -m pip install --no-cache-dir . \
    && addgroup --system --gid 10001 amr \
    && adduser --system --uid 10001 --ingroup amr --home /nonexistent amr

USER 10001:10001

EXPOSE 8080

CMD ["amr-fleet-server"]
