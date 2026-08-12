FROM debian:trixie

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    build-essential \
    clang \
    cmake \
    ccache \
    ninja-build \
    pkg-config \
    git \
    curl \
    libcurl4-openssl-dev \
    libglfw3-dev \
    libuv1-dev \
    libpng-dev \
    libicu-dev \
    libjpeg-dev \
    libwebp-dev \
    libegl1-mesa-dev \
    libgl1-mesa-dev \
    libboost-all-dev \
    liblua5.4-dev \
    libsqlite3-dev \
    rapidjson-dev \
    libshp-dev \
    xvfb \
    vim \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src

