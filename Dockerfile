FROM python:3.13@sha256:37c657465be8871dba2b5f1e32c6664f9862c7573de45c0be92f26bda170770e AS requirements_stage

WORKDIR /wheel

RUN python -m pip install --user uv

COPY ./pyproject.toml \
  ./uv.lock \
  /wheel/

# Export only third-party dependencies. The project source is copied into the
# image later and loaded by NoneBot via ``load_from_toml``, so emitting the
# local ``-e .`` entry would require README.md / license files in this stage
# and is unnecessary.
RUN python -m uv export --format requirements.txt --output-file requirements.txt --no-hashes --no-emit-project

RUN python -m pip wheel --wheel-dir=/wheel --no-cache-dir --requirement ./requirements.txt

RUN python -m uv tool run --no-cache --from nb-cli nb generate -f /tmp/bot.py


FROM python:3.13-slim@sha256:7ba5f5888fbe0014ab9edb2278922995c2201fc3752c46b0be24763eb46fa9f3

WORKDIR /app

ENV TZ=Asia/Shanghai
ENV PYTHONPATH=/app

COPY ./docker/gunicorn_conf.py ./docker/start.sh /
RUN chmod +x /start.sh

ENV APP_MODULE=_main:app
ENV MAX_WORKERS=1

COPY --from=requirements_stage /tmp/bot.py /app
COPY ./docker/_main.py /app
COPY --from=requirements_stage /wheel /wheel

RUN pip install --no-cache-dir gunicorn uvicorn[standard] nonebot2 \
  && pip install --no-cache-dir --no-index --force-reinstall --find-links=/wheel -r /wheel/requirements.txt && rm -rf /wheel
RUN groupadd --system app \
  && useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app \
  && chown -R app:app /app
COPY --chown=app:app . /app/

# Smoke-test mode: expose a build-time flag, copy the entrypoint script and
# install nb-cli only when smoke tests are requested so the production image
# stays unchanged by default.
ARG SMOKE_TEST=false
ENV SMOKE_TEST=${SMOKE_TEST}
COPY --chown=app:app ./docker/smoke-test.py /app/docker/smoke-test.py
RUN if [ "${SMOKE_TEST}" = "true" ]; then pip install --no-cache-dir nb-cli; fi

USER app

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import socket, os; p=int(os.getenv('PORT','8080')); s=socket.socket(); s.connect(('localhost', p)); s.close()"

CMD if [ "${SMOKE_TEST}" = "true" ]; then exec python /app/docker/smoke-test.py; else exec /start.sh; fi
