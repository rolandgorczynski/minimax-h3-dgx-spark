ARG BASE_IMAGE=nvcr.io/nvidia/pytorch:25.11-py3
FROM ${BASE_IMAGE}

ARG COMFYUI_REF=v0.30.0
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_XET_HIGH_PERFORMANCE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      git git-lfs curl ca-certificates ffmpeg \
      libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
      tini procps jq \
    && rm -rf /var/lib/apt/lists/* \
    && git lfs install --system

COPY comfyui-src/ /opt/ComfyUI/

WORKDIR /opt/ComfyUI

# 保留 NGC 镜像内经过验证的 CUDA/PyTorch；禁止 requirements 覆盖 torch。
RUN grep -Ev '^(torch|torchvision|torchaudio)([<=>~! ].*)?$' requirements.txt \
      > /tmp/comfy-requirements.txt \
    && python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install -r /tmp/comfy-requirements.txt \
    && python -m pip install "huggingface_hub[hf_xet]>=0.34.0"

# Build torchaudio against the pinned NGC PyTorch ABI (PyPI wheels are incompatible).
RUN curl -L --retry 3 -o /tmp/torchaudio-src.tar.gz \
      "https://codeload.github.com/pytorch/audio/tar.gz/87ff22e49ed0" \
    && tar xzf /tmp/torchaudio-src.tar.gz -C /tmp \
    && MAX_JOBS=4 python -m pip install --no-build-isolation --no-deps /tmp/audio-87ff22e49ed0 \
    && python -c "import torchaudio; print('torchaudio =', torchaudio.__version__)" \
    && rm -rf /tmp/audio-87ff22e49ed0 /tmp/torchaudio-src.tar.gz

# Freeze installed packages so extension dependencies cannot replace NGC torch/CUDA.
COPY docker/extensions-requirements.txt /tmp/extensions-requirements.txt
RUN python -m pip freeze --all > /tmp/base-constraints.txt \
    && python -m pip install -c /tmp/base-constraints.txt -r /tmp/extensions-requirements.txt \
    && python -c "import cv2, imageio_ffmpeg, color_matcher, mss, torch, torchaudio; print(torch.__version__, torchaudio.__version__)"

RUN chmod -R a+rX /opt/ComfyUI
COPY docker/entrypoint.sh /usr/local/bin/h3-entrypoint
COPY docker/download_models.py /usr/local/bin/h3-download-models
RUN chmod 755 /usr/local/bin/h3-entrypoint /usr/local/bin/h3-download-models

EXPOSE 8188
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/h3-entrypoint"]
