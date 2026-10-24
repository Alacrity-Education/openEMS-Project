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
