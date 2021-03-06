import time

import PyTango
import numpy

import p05.common.PyTangoProxyConstants as proxies
import p05.tools.misc as misc


def ScanPitch(tPitch = None, tQBPM = None, PitchPosArr = None, DeltaRange = 0.0004, NumPoints = 31, AvgPerPoint = 4, Detune = 0.0):
    """
    return values:
        <Bool> :  Max in center
        <Float>:  Value of maximum (fit / edge position)
        <float arr>: Pitch scanning positions
        <float arr>: pitch current results
    """
    # TODO remove if tPitch - make tQBPM be mandatory argument as it is used anyway
    # If you define tPitch as PyTango.DeviceProxy it will be never None
    if tPitch == None:
        print('%s: Error - no pitch motor selected' % misc.GetTimeString())
        return None
    # If you define tPitch only as PyTango.DeviceProxy it will be never 'qbpm2' or 'QBPM2'
    if tPitch == 'qbpm2' or tPitch == 'QBPM2':
        tQBPM = PyTango.DeviceProxy(proxies.tQBPM_i404_exp02)
    # OptimizePitch is used only in NanoScriptHelper were tQBPM is defined as the in the following if.
    # Why not to use already defined tQBPM form NanoScriptHelper?
    if tQBPM == None:
        tQBPM = PyTango.DeviceProxy(proxies.tQBPM_i404_exp01)

    Pitch0 = tPitch.read_attribute('Position').value
    if Detune != 0.0:
        Pitch0 -= Detune
    if PitchPosArr == None:
        PitchPosArr = numpy.linspace(Pitch0 + DeltaRange, Pitch0 - DeltaRange, num=NumPoints, endpoint=True)
    PitchResArr = numpy.zeros((NumPoints))
    while tPitch.state() == PyTango.DevState.MOVING:
        time.sleep(0.1)
    for i in range(PitchPosArr.size):
        tPitch.write_attribute('Position', PitchPosArr[i])
        time.sleep(0.1)
        while tPitch.state() == PyTango.DevState.MOVING:
            time.sleep(0.1)
        for ii in range(AvgPerPoint):
            PitchResArr[i] += 1.0 * tQBPM.read_attribute('PosAndAvgCurr').value[2] / AvgPerPoint
            time.sleep(0.05)
    inum = PitchResArr.argmax()
    if inum == 0 or inum == (PitchResArr.size-1):
        print('%s: Maximum at edge of scan detected. Redo scan!' %misc.GetTimeString())
        FitSuccessful = False
        PitchMaxPos = PitchPosArr[inum]
        tPitch.write_attribute('Position', PitchPosArr[inum] + Detune)
    else:
        FitSuccessful = True
        polyf = numpy.polyfit(PitchPosArr, PitchResArr, deg = 2)
        PitchMaxPos = - polyf[1] / ( 2 * polyf[0])
        if PitchMaxPos > numpy.amin(PitchPosArr) and PitchMaxPos < numpy.amax(PitchPosArr):
            tPitch.write_attribute('Position', PitchMaxPos + Detune)
        else:
            PitchMaxPos = PitchPosArr[inum]
            FitSuccessful = False
            tPitch.write_attribute('Position', PitchPosArr[inum] + Detune)
    time.sleep(0.1)
    while tPitch.state() == PyTango.DevState.MOVING:
            time.sleep(0.1)
    return FitSuccessful, PitchMaxPos, PitchPosArr, PitchResArr

def OptimizePitch(tPitch, tQBPM=None, PitchPosArr=None, DeltaRange=0.0004, NumPoints=31, AvgPerPoint=4, Detune=0.0):
    t0 = time.time()
    while True:
        c0, c1, c2, c3 = ScanPitch(tPitch=tPitch, tQBPM=tQBPM, PitchPosArr=PitchPosArr, \
                                   DeltaRange=DeltaRange, NumPoints=NumPoints, AvgPerPoint=AvgPerPoint, Detune=Detune)
        if c0 == True:
            print('%s: Fit of pitch position succeeded.' % misc.GetTimeString())
            break
        elif c0 == False:
            if abs(c2[0] - c1) < abs(c2[-1] - c1):
                delta = 0.8 * DeltaRange
            else:
                delta = -0.8 * DeltaRange
            tPitch.write_attribute('Position', c1 + delta)
        if time.time() - t0 > 300:
            print('%s: Warning: Iteration timeout. Retry.' %misc.GetTimeString())
            break
    return None