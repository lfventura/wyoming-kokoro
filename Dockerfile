FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/hf \
    HOME=/tmp

RUN pip install --index-url https://download.pytorch.org/whl/cpu torch==2.8.0 \
 && pip install kokoro==0.9.4 wyoming==1.10.2 sentence-stream==1.3.0

# Bake the model and voice packs into the image: no downloads at runtime, works for any UID.
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download('hexgrad/Kokoro-82M', allow_patterns=['config.json', 'kokoro-v1_0.pth', 'voices/*'])" \
 && chmod -R a+rX /opt/hf

ENV HF_HUB_OFFLINE=1

WORKDIR /app
COPY wyoming_kokoro ./wyoming_kokoro

EXPOSE 10200
ENTRYPOINT ["python", "-m", "wyoming_kokoro"]
