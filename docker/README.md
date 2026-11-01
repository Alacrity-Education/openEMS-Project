# openEMS SYCL image

openEMS built with the SYCL GPU backend (Intel GPUs through Level Zero, ahead of
time for Arc B580 `bmg-g21`, SPIR-V for other Intel GPUs) plus
[gerber2ems](https://github.com/antmicro/gerber2ems), laid out like the antmicro
gerber2ems image: user `docker`, openEMS in `/home/docker/opt/openEMS`, its
Python venv (openEMS, CSXCAD, gerber2ems, scikit-rf, h5py, matplotlib, vtk) in
`/home/docker/opt/openEMS/venv`, entrypoint `gerber2ems`. It carries the oneAPI
SYCL runtime and the Intel GPU compute runtime; the kernel driver is the host's.

```bash
docker pull ghcr.io/alacrity-education/openems-sycl:latest
```

## GPU

Pass the render node and its group:

```bash
docker run --rm --device /dev/dri --group-add $(stat -c %g /dev/dri/renderD128) ...
```

Select the GPU engine with `--engine=gpu` on the openEMS command line or
`FDTD.Run(sim_path, engine='gpu')` in Python (`gpu_device=N` picks a device);
`-vv` / `verbose=2` prints the device and whether every extension runs on it.
Tuning/debug knobs, defaults are the validated ones: `OPENEMS_SYCL_KERNEL_TIMES=1`,
`OPENEMS_SYCL_FUSED_STEP=0|1`, `OPENEMS_SYCL_INDEX=32|64`, `OPENEMS_SYCL_UPML_FUSION=0`.

## Drop-in for gerber2ems:latest

```bash
docker run --rm --user $(id -u):$(id -g) -e HOME=/tmp -v "$PWD:/work" -w /work \
  --device /dev/dri --group-add $(stat -c %g /dev/dri/renderD128) \
  --entrypoint /home/docker/opt/openEMS/venv/bin/python \
  ghcr.io/alacrity-education/openems-sycl:latest sim_pi.py ...
```

The same invocation as before, with the image name replaced and the two GPU
options added; without them the CPU engines run as usual.

## Build locally

```bash
docker build -t openems-sycl -f docker/Dockerfile docker/ \
  --build-arg PROJECT_REPO=https://github.com/Alacrity-Education/openEMS-Project.git \
  --build-arg PROJECT_REF=sycl-backend
```

`PROJECT_REF` is a branch, tag or commit; the Dockerfile clones it with its
submodules. A branch name is cached by Docker like any other build argument:
pass a commit (or `--no-cache`) to pick up new pushes. `ONEAPI_VERSION` selects
the oneAPI compiler and runtime (default 2026.0.0-947).

## Build locally for `integration/october`

The branch `integration/october` pins openEMS to its `integration/october`
(the optimized SYCL backend with the setup optimizations: the operator
fingerprint, phase times and cache, the exact CPU fixes of the operator build
and its material pass on the GPU) and CSXCAD to the
[Alacrity-Education fork](https://github.com/Alacrity-Education/CSXCAD)'s
`integration/october` (constant material weights, `HasConstantWeights()`).
Build it from a commit of the branch, so that no cached clone of an older push
is reused:

```bash
REF=$(git ls-remote https://github.com/Alacrity-Education/openEMS-Project.git \
      refs/heads/integration/october | cut -f1)
docker build -f docker/Dockerfile docker/ --build-arg PROJECT_REF=$REF \
  -t openems-sycl:integration-october
docker tag openems-sycl:integration-october openems-sycl:latest
docker builder prune -f    # the builder stage leaves several GB of cache
```

The image is the same as above; nothing more is needed at run time for the
setup pass, which runs in the SYCL plugin. Pass the render node of one GPU only,
found by its PCI address (the `renderD` numbers can change between boots):

```bash
ls -l /dev/dri/by-path/                      # e.g. pci-0000:87:00.0-render -> ../renderD130
DEV=$(readlink -f /dev/dri/by-path/pci-0000:87:00.0-render)
docker run --rm --device $DEV openems-sycl:integration-october \
  /home/docker/opt/openEMS/bin/openEMS --version
```

Add `--group-add $(stat -c %g $DEV)` where the render node is not readable by
everyone. The setup pass prints `setup device: SYCL (<GPU>), ... pass <s>` at
`-vv` (`OPENEMS_SETUP_DEVICE=0` takes the CPU path, with the same result);
`OPENEMS_OPERATOR_FINGERPRINT=1` and `OPENEMS_SETUP_TIMES=1` print the operator
hashes and the phase times, `OPENEMS_OPERATOR_CACHE=<dir>` keeps the operator
across runs of one geometry.

## A simulation image on top of this one

A simulation is a small image `FROM openems-sycl:integration-october` with the
script, run with the venv's Python; its results go to a bind mount.
`examples/msl_notch_filter/` is the MSL notch filter tutorial of openEMS with
`engine='gpu'` (about 12000 timesteps of 0.27 Mcells, a few seconds on an
Arc B580), writing `NotchFilter/` (the probes), `notch_s_params.csv` and
`notch_s_params.png` to `/work`:

```bash
docker build -t openems-sim-example docker/examples/msl_notch_filter
mkdir -p out
docker run --rm --device $(readlink -f /dev/dri/by-path/pci-0000:87:00.0-render) \
  --user $(id -u):$(id -g) -e HOME=/tmp -v "$PWD/out:/work" openems-sim-example
```

The Dockerfile of the example:

```dockerfile
ARG BASE_IMAGE=openems-sycl:integration-october
FROM ${BASE_IMAGE}
COPY msl_notch_filter.py /home/docker/sim/msl_notch_filter.py
WORKDIR /work
ENTRYPOINT ["/home/docker/opt/openEMS/venv/bin/python", "/home/docker/sim/msl_notch_filter.py"]
```
