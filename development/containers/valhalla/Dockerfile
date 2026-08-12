# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

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
    wget \
    unzip \
    jq \
    autoconf \
    automake \
    libtool \
    libboost-all-dev \
    libprotobuf-dev \
    protobuf-compiler \
    libsqlite3-dev \
    libspatialite-dev \
    spatialite-bin \
    libcurl4-openssl-dev \
    liblz4-dev \
    libzmq3-dev \
    libczmq-dev \
    libgeotiff-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
