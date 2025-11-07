# ClusterFuzzLite Dockerfile for Image Preprocessing Detector
# Python fuzzing environment with Atheris and dependencies

FROM gcr.io/oss-fuzz-base/base-builder-python

# Install system dependencies for image/PDF processing
RUN apt-get update && apt-get install -y \
    clang \
    llvm \
    lld \
    libpoppler-cpp-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set up Python 3.11 for fuzzing
# Note: Project requires Python 3.12, but Atheris doesn't support PRECALL opcode changes in 3.12
# Using Python 3.11 as closest compatible version (base image only provides Python 3.8)
# Install from deadsnakes PPA to get Python 3.11
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y python3.11 python3.11-dev python3.11-distutils && \
    rm -rf /var/lib/apt/lists/*

# Make Python 3.11 the default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Ensure pip is properly installed for Python 3.11
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

# Copy project source
COPY . $SRC/image-preprocessing-detector
WORKDIR $SRC/image-preprocessing-detector

# Install Poetry
RUN pip3 install poetry

# Install project dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --without dev --no-interaction

# Install Atheris fuzzing engine
RUN pip3 install atheris

# Copy fuzzing harnesses
COPY fuzz/*.py $OUT/
