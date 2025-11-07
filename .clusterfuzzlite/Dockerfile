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

# Set up Python 3.11 (required for Atheris compatibility)
RUN apt-get update && apt-get install -y python3.11 python3.11-dev && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

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
