FROM pytorch/pytorch:2.4.0-cuda11.8-cudnn9-runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    TZ=Etc/UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY ./requirements.txt /workspace/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /workspace/requirements.txt

COPY ./src /workspace/src

WORKDIR /workspace/src

CMD ["python", "-u", "train.py"]
#CMD ["bash", "-c", "python --version && nvidia-smi"]
