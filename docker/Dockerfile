# openEMS with the SYCL GPU backend (Intel GPUs, Level Zero) and gerber2ems.
# Same layout as the antmicro gerber2ems image: user docker, openEMS in
# /home/docker/opt/openEMS, its venv in /home/docker/opt/openEMS/venv.
#
#   docker build -t openems-sycl -f docker/Dockerfile docker/

ARG BASE_IMAGE=ubuntu:24.04

# --- apt repositories of Intel oneAPI and of the GPU compute runtime (Intel's
# kobuk-team PPA: the runtime of repositories.intel.com/gpu, 25.18, aborts at exit
# on hosts with an i915 iGPU next to the Arc card), user docker ---
FROM ${BASE_IMAGE} AS base
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl gpg \
 && curl -fsSL https://apt.repos.intel.com/intel-gpg-keys/GPG-PUB-KEY-INTEL-SW-PRODUCTS.PUB \
    | gpg --dearmor -o /usr/share/keyrings/oneapi-archive-keyring.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/oneapi-archive-keyring.gpg] https://apt.repos.intel.com/oneapi all main" \
    > /etc/apt/sources.list.d/oneAPI.list \
 && curl -fsSL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x0C0E6AF955CE463C03FC51574D098D70AFBE5E1F" \
    | gpg --dearmor -o /usr/share/keyrings/intel-graphics.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/intel-graphics.gpg] https://ppa.launchpadcontent.net/kobuk-team/intel-graphics/ubuntu noble main" \
    > /etc/apt/sources.list.d/intel-graphics.list \
 && rm -rf /var/lib/apt/lists/*
# uid 1000 as in the gerber2ems image (Ubuntu's own user ubuntu has it); home
# readable by others for `docker run --user $(id -u):$(id -g)`
RUN (userdel -r ubuntu 2>/dev/null || true) \
 && useradd -m -u 1000 -s /bin/bash docker && chmod 755 /home/docker
ENV HOME="/home/docker" \
    XDG_CONFIG_HOME="/home/docker/.config" \
    XDG_DATA_HOME="/home/docker/.local/share" \
    XDG_BIN_HOME="/home/docker/.local/bin" \
    PATH="/home/docker/.local/bin:$PATH"
WORKDIR /home/docker

# --- builder: icpx, ocloc (ahead-of-time compile for bmg-g21), the build deps ---
FROM base AS builder
# oneAPI DPC++ compiler version; the runtime stage installs the same version
ARG ONEAPI_VERSION=2026.0.0-947
ARG PROJECT_REPO=https://github.com/Alacrity-Education/openEMS-Project.git
# branch, tag or commit
ARG PROJECT_REF=sycl-backend
# antmicro/gerber2ems main
ARG GERBER2EMS_REF=39d13fc60a6940214a47ffbcf2e164f2c6533b61
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends git intel-ocloc \
    "intel-oneapi-compiler-dpcpp-cpp-${ONEAPI_VERSION%.*}=${ONEAPI_VERSION}" \
 && rm -rf /var/lib/apt/lists/*
# not shallow: the versions come from git describe
USER docker
RUN git clone "${PROJECT_REPO}" openEMS-Project \
 && cd openEMS-Project \
 && git checkout "${PROJECT_REF}" \
 && git submodule update --init --recursive
USER root
RUN apt-get update \
 && openEMS-Project/scripts/install_deps.sh --auto --python --disable-gui \
 && rm -rf /var/lib/apt/lists/*
USER docker
RUN cd openEMS-Project \
 && { ./update_openEMS.sh /home/docker/opt/openEMS --python --disable-GUI --njobs="$(nproc)" \
      || { tail -n 100 build_*.log; exit 1; }; } \
 && grep -h "SYCL GPU backend enabled" build_*.log \
 && test -f /home/docker/opt/openEMS/lib/openEMS/plugins/openEMS_gpu_sycl.so
RUN /home/docker/opt/openEMS/venv/bin/pip install --no-cache-dir \
      "gerber2ems @ git+https://github.com/antmicro/gerber2ems@${GERBER2EMS_REF}" \
      scikit-rf h5py matplotlib vtk \
 && mkdir -p /home/docker/.local/bin \
 && ln -s /home/docker/opt/openEMS/venv/bin/{gerber2ems,ems2paraview,ems2png} /home/docker/.local/bin

# --- runtime: no compiler; oneAPI SYCL runtime of the same version, GPU compute runtime ---
FROM base
ARG ONEAPI_VERSION=2026.0.0-947
ARG DEBIAN_FRONTEND=noninteractive
LABEL org.opencontainers.image.source="https://github.com/Alacrity-Education/openEMS-Project" \
      org.opencontainers.image.description="openEMS with the SYCL GPU backend (Intel GPUs) and gerber2ems" \
      org.opencontainers.image.licenses="GPL-3.0-or-later"
# the libraries openEMS links, python for the venv, gerbv for gerber2ems;
# the SYCL runtime (/opt/intel/oneapi/redist/lib, in ld.so.conf), no CPU OpenCL/TBB
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    libboost-program-options1.83.0 libboost-thread1.83.0 libhdf5-103-1t64 libhdf5-hl-100t64 \
    libtinyxml2.6.2v5 zlib1g python3 python3-venv gerbv \
    libze1 libze-intel-gpu1 intel-opencl-icd \
    "intel-oneapi-runtime-dpcpp-sycl-core=${ONEAPI_VERSION}" \
    "intel-oneapi-runtime-compilers=${ONEAPI_VERSION}" \
    "intel-oneapi-runtime-compilers-common=${ONEAPI_VERSION}" \
    "intel-oneapi-runtime-openmp=${ONEAPI_VERSION}" \
 && rm -rf /var/lib/apt/lists/*
# libumf, which the Level Zero adapter of the SYCL runtime needs, is in no runtime package
COPY --from=builder /opt/intel/oneapi/umf /opt/intel/oneapi/umf
RUN echo /opt/intel/oneapi/umf/latest/lib > /etc/ld.so.conf.d/intel-oneapi-umf.conf && ldconfig
COPY --from=builder --chown=docker:docker /home/docker/opt /home/docker/opt
COPY --from=builder --chown=docker:docker /home/docker/.local /home/docker/.local
USER docker
# everything resolves without setvars.sh (no GPU needed for this); the plugin is
# loaded by libopenEMS, hence $P/lib for ldd only
RUN P=/home/docker/opt/openEMS \
 && for f in $P/lib/openEMS/plugins/openEMS_gpu_sycl.so /opt/intel/oneapi/redist/lib/libur_adapter_level_zero.so.0; do \
      LD_LIBRARY_PATH=$P/lib ldd "$f" | { ! grep "not found"; } || exit 1; done \
 && $P/bin/openEMS --help > /dev/null \
 && $P/venv/bin/python -c "import openEMS, CSXCAD, skrf, vtk, numpy, h5py, matplotlib" \
 && gerber2ems --help > /dev/null
ENTRYPOINT ["gerber2ems"]
