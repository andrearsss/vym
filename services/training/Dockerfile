FROM ultralytics/ultralytics:latest-python-export@sha256:1ab67444c3dad2b7abbafaa300f55d75a2b9e730bcb24c345fd7264e60da669e

WORKDIR /workspace

COPY ./requirements.txt /workspace/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /workspace/requirements.txt

CMD ["sleep", "infinity"] 
