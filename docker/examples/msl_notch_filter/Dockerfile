# A simulation on top of the openEMS SYCL image: the MSL notch filter tutorial
# on the GPU engine, results in the bind-mounted /work.
#
#   docker build -t openems-sim-example docker/examples/msl_notch_filter
#   docker run --rm --device $(readlink -f /dev/dri/by-path/pci-<address>-render) \
#     --user $(id -u):$(id -g) -e HOME=/tmp -v "$PWD/out:/work" openems-sim-example
#
# The GPU is named by its PCI address (ls -l /dev/dri/by-path/): the renderD
# numbers can change between boots and belong to different cards.

ARG BASE_IMAGE=openems-sycl:integration-october
FROM ${BASE_IMAGE}
COPY msl_notch_filter.py /home/docker/sim/msl_notch_filter.py
WORKDIR /work
ENTRYPOINT ["/home/docker/opt/openEMS/venv/bin/python", "/home/docker/sim/msl_notch_filter.py"]
