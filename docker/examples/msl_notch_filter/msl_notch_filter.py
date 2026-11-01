# -*- coding: utf-8 -*-
"""
 Microstrip Notch Filter Tutorial

 Tested with
  - python 3.14
  - openEMS v0.37

 (c) 2016-2023 Thorsten Liebig <thorsten.liebig@gmx.de>
 15-Dec-2025: modified to use matplotlib.pyplot instead of pylab
 2026: the example simulation of docker/README.md: the GPU engine, results in
       /work (a bind mount), no window (the plot goes to a file)

"""

### Import Libraries
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')  # no display in the container
import matplotlib.pyplot as plt  # pip install matplotlib

from CSXCAD  import ContinuousStructure
from openEMS import openEMS
from openEMS.physical_constants import *


### Setup the simulation
out_dir = os.environ.get('SIM_OUT', '/work')
Sim_Path = os.path.join(out_dir, 'NotchFilter')
post_proc_only = False

unit = 1e-6 # specify everything in um
MSL_length = 50000
MSL_width = 600
substrate_thickness = 254
substrate_epr = 3.66
stub_length = 12e3
f_max = 7e9

### Setup FDTD parameters & excitation function
FDTD = openEMS()
FDTD.SetGaussExcite( f_max/2, f_max/2 )
FDTD.SetBoundaryCond( ['PML_8', 'PML_8', 'MUR', 'MUR', 'PEC', 'MUR'] )

### Setup Geometry & Mesh
CSX = ContinuousStructure()
FDTD.SetCSX(CSX)
mesh = CSX.GetGrid()
mesh.SetDeltaUnit(unit)

resolution = C0/(f_max*np.sqrt(substrate_epr))/unit/50 # resolution of lambda/50
third_mesh = np.array([2*resolution/3, -resolution/3])/4

## Do manual meshing
mesh.AddLine('x', 0)
mesh.AddLine('x',  MSL_width/2+third_mesh)
mesh.AddLine('x', -MSL_width/2-third_mesh)
mesh.SmoothMeshLines('x', resolution/4)

mesh.AddLine('x', [-MSL_length, MSL_length])
mesh.SmoothMeshLines('x', resolution)

mesh.AddLine('y', 0)
mesh.AddLine('y',  MSL_width/2+third_mesh)
mesh.AddLine('y', -MSL_width/2-third_mesh)
mesh.SmoothMeshLines('y', resolution/4)

mesh.AddLine('y', (MSL_width/2+stub_length)+third_mesh)
mesh.AddLine('y', [-15*MSL_width, 15*MSL_width+stub_length])
mesh.SmoothMeshLines('y', resolution)

mesh.AddLine('z', np.linspace(0,substrate_thickness,5))
mesh.AddLine('z', 3000)
mesh.SmoothMeshLines('z', resolution)

## Add the substrate
substrate = CSX.AddMaterial( 'RO4350B', epsilon=substrate_epr)
start = [mesh.GetLine('x', 0) , mesh.GetLine('y', 0) , 0]
stop  = [mesh.GetLine('x', -1), mesh.GetLine('y', -1), substrate_thickness]
substrate.AddBox(start, stop)

## MSL port setup
port = [None, None]
pec = CSX.AddMetal( 'PEC' )
portstart = [ -MSL_length, -MSL_width/2, substrate_thickness]
portstop  = [ 0,  MSL_width/2, 0]
port[0] = FDTD.AddMSLPort( 1,  pec, portstart, portstop, 'x', 'z', excite=-1, FeedShift=10*resolution, MeasPlaneShift=MSL_length/3, priority=10)

portstart = [MSL_length, -MSL_width/2, substrate_thickness]
portstop  = [0         ,  MSL_width/2, 0]
port[1] = FDTD.AddMSLPort( 2, pec, portstart, portstop, 'x', 'z', MeasPlaneShift=MSL_length/3, priority=10 )

## Filter-Stub Definition
start = [-MSL_width/2,  MSL_width/2, substrate_thickness]
stop  = [ MSL_width/2,  MSL_width/2+stub_length, substrate_thickness]
pec.AddBox(start, stop, priority=10 )

### Run the simulation
if 0:  # debugging only
    CSX_file = os.path.join(Sim_Path, 'notch.xml')
    if not os.path.exists(Sim_Path):
        os.mkdir(Sim_Path)
    CSX.Write2XML(CSX_file)
    from CSXCAD import AppCSXCAD_BIN
    os.system(AppCSXCAD_BIN + ' "{}"'.format(CSX_file))


if not post_proc_only:
    # engine='gpu': the SYCL backend on the Intel GPU passed to the container;
    # verbose=2 prints the device and the setup pass
    FDTD.Run(Sim_Path, cleanup=True, engine='gpu', verbose=2)

### Post-processing and plotting
f = np.linspace( 1e6, f_max, 1601 )
for p in port:
    p.CalcPort( Sim_Path, f, ref_impedance = 50)

s11 = port[0].uf_ref / port[0].uf_inc
s21 = port[1].uf_ref / port[0].uf_inc

## Save the s-parameters
np.savetxt(os.path.join(out_dir, 'notch_s_params.csv'),
           np.column_stack([f, 20*np.log10(abs(s11)), 20*np.log10(abs(s21))]),
           delimiter=',', header='f_Hz,S11_dB,S21_dB', comments='')

## Plot s-parameter

fig, axis = plt.subplots(num="S11", tight_layout=True)
axis.plot(f/1e9, 20*np.log10(abs(s11)), 'k-',  linewidth=2, label='$S_{11}$')
axis.plot(f/1e9, 20*np.log10(abs(s21)), 'r--',  linewidth=2, label='$S_{21}$')
axis.grid()
axis.set_xmargin(0)
axis.set_xlabel('Frequency (GHz)')
axis.set_ylabel('S-Parameter (dB)')
axis.legend()

fig.savefig(os.path.join(out_dir, 'notch_s_params.png'))
print('written:', ', '.join(sorted(os.listdir(out_dir))))
