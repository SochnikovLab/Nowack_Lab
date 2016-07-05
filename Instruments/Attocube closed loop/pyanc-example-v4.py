#
# PyANC350v4 example file
#   by Brian Schaefer, adapted from pyanc-example.py by Rob Heath
#

import PyANC350v4
import time

ax = {'x':0,'y':1,'z':2}
#define a dict of axes to make things simpler

anc = PyANC350v4.Positioner()
#instantiate positioner as anc
print('-------------------------------------------------------------')
print('capacitances:')
for axis in sorted(ax.keys()):
    print(axis,anc.measureCapacitance(ax[axis]))
# print('-------------------------------------------------------------')
# print('setting static amplitude to 2V')
# anc.staticAmplitude(2000)
# #set staticAmplitude to 2V to ensure accurate positioning info
# staticAmplitude function does not exist in v4
print('-------------------------------------------------------------')
print('moving to x = 2mm')
anc.setTargetPosition(ax['x'], 2e-3)
anc.startAutoMove(ax['x'], 1, 0)

#check what's happening
time.sleep(0.5)
moving = 1
while moving == 1:
    connected, enabled, moving, target, eotFwd, eotBwd, error = anc.getAxisStatus(ax['x']) #find bitmask of status
    if moving == 1:
        print('axis moving, currently at',anc.getPosition(ax['x']))
    elif moving == 0:
        print('axis arrived at',anc.getPosition(ax['x']))
    time.sleep(0.5)

print('and moving y:')
anc.setTargetPosition(ax['x'], 2e-3)
anc.startAutoMove(ax['x'], 1, 0)
time.sleep(0.5)
moving = 1
while moving == 1:
    connected, enabled, moving, target, eotFwd, eotBwd, error = anc.getAxisStatus(ax['x']) #find bitmask of status
    if moving == 1:
        print('axis moving, currently at',anc.getPosition(ax['x']))
    elif moving == 0:
        print('axis arrived at',anc.getPosition(ax['x']))
    time.sleep(0.5)

    
print('-------obtaining all possible gettable values for x---------')
#get every possible gettable value
print('getActuatorName',anc.getActuatorName(ax['x']))
print('getActuatorType',anc.getActuatorType(ax['x']))
print('getAmplitude',anc.getAmplitude(ax['x']))
print('getAxisStatus',anc.getAxisStatus(ax['x']))
print('getDeviceConfig',anc.getDeviceConfig())
print('getDeviceInfo',anc.getDeviceInfo())
print('getFirmwareVersion',anc.getFirmwareVersion())
print('getFrequency',anc.getReference(ax['x']))
print('getPosition',anc.getPosition(ax['x']))
print('-------------------------------------------------------------')

print('testing \'functions for manual positioning\'')
anc.setFrequency(ax['x'],50)
print('set frequency to 50Hz')
for i in range(30):
    anc.startSingleStep(ax['x'],0)
    time.sleep(0.1)
print('arrived at:',anc.getPosition(ax['x']),'after 30 pulses')
anc.startContinousMove(ax['x'],1, 0)
print('waiting 3 seconds...')
time.sleep(3)
anc.startContinousMove(ax['x'],0, 0)
print('and stopped at',anc.getPosition(ax['x']))
print('set frequency to 200Hz')
anc.setFrequency(ax['x'],200)
anc.startContinousMove(ax['x'],1, 0)
print('waiting 3 seconds...')
time.sleep(3)
anc.startContinousMove(ax['x'],0, 0)

print('-------------------------------------------------------------')
print('closing connection...')
anc.close()
print('-------------------------------------------------------------')
