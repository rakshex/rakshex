# The worker accepts only the resulting immutable sha256 image ID/digest.
# Build/pull this image out of band; untrusted jobs cannot install dependencies.
FROM python:3.12-slim
RUN groupadd --gid 65532 sandbox && useradd --uid 65532 --gid 65532 --no-create-home sandbox
COPY check.py /opt/rakshex/check.py
USER 65532:65532
WORKDIR /work
ENTRYPOINT ["python", "-I", "-B", "/opt/rakshex/check.py"]
