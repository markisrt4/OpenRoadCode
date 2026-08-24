# syntax=docker/dockerfile:1.7
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

ARG DEBIAN_BASE=debian:trixie-slim
FROM ${DEBIAN_BASE}
ARG TILEMAKER_COMMIT=bf89810199519d3e89bd4ace323aec4d41d2d8a6
ARG VALHALLA_COMMIT=a60c7cbfc83e073f50887cd27e0109d02e6b64e5
ARG GLYPHS_COMMIT=c17d4e2840fb583c0cddfb310804a75de74099a8
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        cmake \
        curl \
        git \
        jq \
        make \
        ninja-build \
        pkg-config \
        python3 \
        python3-venv \
        sqlite3 \
        sudo \
        wget \
        osmium-tool \
        rsync \
        libboost-filesystem-dev \
        libboost-iostreams-dev \
        libboost-program-options-dev \
        liblua5.4-dev \
        libprotobuf-dev \
        protobuf-compiler \
        libshp-dev \
        libsqlite3-dev \
        rapidjson-dev \
        zlib1g-dev \
        libzstd-dev \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/systemed/tilemaker.git /opt/tilemaker \
     && git -C /opt/tilemaker checkout "${TILEMAKER_COMMIT}" \
     && cmake \
         -S /opt/tilemaker \
         -B /opt/tilemaker/build \
     && cmake --build /opt/tilemaker/build -j"$(nproc)" \
     && cmake --install /opt/tilemaker/build \
     && ldconfig

RUN git clone --recurse-submodules \
         https://github.com/valhalla/valhalla.git \
         /opt/valhalla \
    && git -C /opt/valhalla checkout "${VALHALLA_COMMIT}" \
    && git -C /opt/valhalla submodule update --init --recursive \
    && bash /opt/valhalla/scripts/install-linux-deps.sh \
    && cmake \
        -S /opt/valhalla \
        -B /opt/valhalla/build \
        -DCMAKE_BUILD_TYPE=Release \
        -DENABLE_TESTS=OFF \
        -DENABLE_BENCHMARKS=OFF \
        -DENABLE_PYTHON_BINDINGS=OFF \
        -DENABLE_TOOLS=ON \
        -DENABLE_DATA_TOOLS=ON \
        -DENABLE_SERVICES=ON \
        -DENABLE_SINGLE_FILES_WERROR=OFF \
    && cmake --build /opt/valhalla/build -j"$(nproc)" \
    && cmake --install /opt/valhalla/build \
    && ldconfig
RUN git clone \
        https://github.com/klokantech/klokantech-gl-fonts.git \
        /opt/klokantech-gl-fonts \
    && git -C /opt/klokantech-gl-fonts checkout "${GLYPHS_COMMIT}"
COPY builder /opt/openroadcode-map-builder/builder
COPY templates /opt/openroadcode-map-builder/templates
COPY toolchain.lock /opt/openroadcode-map-builder/toolchain.lock
ENV PYTHONPATH=/opt/openroadcode-map-builder
ENV OPENROAD_OUTPUT_ROOT=/srv/openroadcode
ENV OPENROAD_CACHE_ROOT=/cache
ENV OPENROAD_SCRATCH_ROOT=/scratch
ENV OPENROAD_STYLE_TEMPLATE=/opt/openroadcode-map-builder/templates/openroadcode-style.json
WORKDIR /work
ENTRYPOINT ["python3", "-m", "builder"]
CMD ["tui"]
