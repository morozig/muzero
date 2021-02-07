FROM tensorflow/tensorflow:2.1.0-gpu

RUN apt-get update && apt-get install -y python3.7 \
    python3-pip \
    ffmpeg \
    libsm6 \
    libxext6

RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.7 1
RUN update-alternatives --set python3 /usr/bin/python3.7

RUN python3.7 -m pip --no-cache-dir install --upgrade pip
RUN rm -f /usr/local/bin/python
RUN ln -s $(which python3) /usr/local/bin/python

RUN python3.7 -m pip install tensorflow==2.1.0 \
    gym \
    gym[atari] \
    tqdm \
    keras==2.3.1 \
    h5py==2.10.0
