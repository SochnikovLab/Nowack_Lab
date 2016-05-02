from instrumental.drivers.daq import ni
from instrumental import u
import numpy
import PyDAQmx as mx
import time
from copy import copy

class NIDAQ():
    '''
    For remote operation of the NI DAQ-6363. Slightly simplified version of Guen's squidpy driver, does not import/inherit anything from squidpy. Uses package Instrumental from Mabuchi lab at Stanford
    '''
    
    def __init__(self, zero=True, freq=100, dev_name='Dev1'):
        self._daq  = ni.NIDAQ(dev_name)
        self._freq = {}
            
        for chan in self._daq.get_AI_channels():
            setattr(NIDAQ,chan,property(fget=eval('lambda self: self.get_chan(\'%s\')' %chan))) # set up property for input channels NIDAQ.ai#(0-31)
        
        for chan in self._daq.get_AO_channels():
        
            setattr(self, '_%s' %chan, None)# privately store value
            # The following line works with instrumental modified to add read function to AnalogOut
            setattr(NIDAQ,chan,property(fset=eval('lambda self, value: self.set_chan(\'%s\',value)' %chan), fget=eval('lambda self: self.get_chan(\'%s\')' %chan)))
            # This works with instrumental after names of input channels added manually
            # setattr(NIDAQ,chan,property(fset=eval('lambda self, value: self.set_chan(\'%s\',value)' %chan), fget=eval('lambda self: self.get_chan(\'_%s_vs_aognd\')' %chan)))
            # This works with the current code, since I couldn't figure out internal channels with instrumental:
            # setattr(NIDAQ,chan,property(fset=eval('lambda self, value: self.set_chan(\'%s\',value)' %chan), fget=eval('lambda self: self.get_internal_chan(\'%s\')' %chan))) #property for output channels NIDAQ.ao# (0-3); monitor using internal channels
            self._freq[chan] = freq

            # DEBUG
        # for chan in ['ao0_vs_aognd', 'ao1_vs_aognd']:
            # setattr(self._daq, chan, ni.AnalogIn(self._daq, '%s'%chan))
            # setattr(NIDAQ,chan,property(fget=eval('lambda self: self.get_chan(\'%s\')' %chan)))
            # print(chan)
            
        
        if zero:
            self.zero()
        
    @property
    def freq(self):
        return self._freq
        
    @freq.setter
    def freq(self, value):
        self._freq = value      

    def get(self):
        for chan in self._daq.get_AO_channels() + self._daq.get_AI_channels():
            print('%s: ' %chan, getattr(self, chan),'\n')
            
    def get_chan(self, chan):
        return getattr(self._daq,chan).read().magnitude

    def set_chan(self, chan, data):
        setattr(self, '_%s' %chan, data)
        if numpy.isscalar(data):
            getattr(self._daq,chan).write('%sV' %data)
    
    def monitor(self, chan_in, duration, freq=100): # similar to send_receive definition; haven't yet built in multiple channels
        received = getattr(self._daq, chan_in).read(duration = '%fs' %duration, fsamp='%fHz' %freq)
        data_in = received[bytes(chan_in, 'utf-8')].magnitude
        t = received['t'].magnitude
        return list(data_in), list(t)
    
    def send_receive(self, chan_out, chan_in, orig_data, freq=100):
        """
         chan_out is list of output channel names, data is list of datasets sent to each channel, in order
         """
        # gotta make these all lists, following code assumes they are list or dict
        data = copy(orig_data) # so we don't modify original data
        
        if numpy.isscalar(chan_out):
            data = {chan_out: data}
            chan_out = [chan_out]
            

        if numpy.isscalar(chan_in):
            chan_in = [chan_in]

        if len(chan_out) != len(data):
            raise Exception('Must have data for each output channel!')

        taskargs = tuple([getattr(self._daq, ch) for ch in chan_out + chan_in])
        task = ni.Task(*taskargs) # * will take tuple as args
        write_data = {}
       
        
        for ch in chan_out: # handle outputs for each channel
            d = data[ch]
            setattr(self, ch, d[0]) # initialize output
       
            # Weird thing to fix daq issue giving data points late by 1.. appears to only happen with lowest numbered output listed :/
            d = list(d) 
            d = d + [d[len(d)-1]]
            # if ch == min_chan: # the lowest numbered channel
                # d = d + [d[len(d)-1]] # For the first one, the first data point is garbage, let's send the last data point twice to get that extra point again
            # else:
                # d = [d[0]] + d #Every other one is fine, so let's just duplicate the first point and get rid of it later
            data[ch] = d
            write_data[ch] = d * u.V # u.V is units, done to make Instrumental happy
   
        task.set_timing(n_samples = len(data[chan_out[0]]), fsamp='%fHz' %freq) 

        received = task.run(write_data)
        data_in = {}
        
        # Find lowest number channel, need to do this because the lowest number input channel will have garbage point. it's the lowest number because I modded instrumental to order them from low to high. It's really whichever channel is specified first.
        ch_nums = [int(''.join(x for x in y if x.isdigit())) for y in chan_in] #finds the channel numbers    
        min_chan = 'ai%i' %min(ch_nums)
        
        for ch in chan_in:
            d = received[ch].magnitude #.magnitude from pint units package; 
            if ch == min_chan:#chan_in[0]:
                data_in[ch] = list(d[1:len(d)]) # get rid of the first data point because of the weird thing we died earlier
            else:
                data_in[ch] = list(d[0:len(d)-1]) # last data point should be a dupe
        time = received['t'].magnitude
        
        return data_in, list(time[0:len(time)-1]) #list limits undo extra point added for daq weirdness
        
    def sweep(self, chan_out, chan_in, Vstart, Vend, freq=100, numsteps=1000):   
        V = {}       
        for k in Vstart.keys():        
            V[k] = list(numpy.linspace(Vstart[k], Vend[k], numsteps))
            if max(abs(Vstart[k]), abs(Vend[k])) > 10:
                raise Exception('NIDAQ out of range!')
            
        response, time = self.send_receive(chan_out, chan_in, V, freq=freq)
         
        return V, response, time
        
    def zero(self):
        for chan in self._daq.get_AO_channels():
            self.sweep(chan, 'ai0', {chan: getattr(self, chan)}, {chan: 0})
                        
    def get_internal_chan(self, chan):
        """
        Modifies example of PyDAQmx from https://pythonhosted.org/PyDAQmx/usage.html#task-object .
        """
        analog_input = mx.Task()
        read = mx.int32()
        data = numpy.zeros((1,), dtype=numpy.float64)

        # DAQmx Configure Code
        analog_input.CreateAIVoltageChan("Dev1/_%s_vs_aognd" %chan,"",mx.DAQmx_Val_Cfg_Default,-10.0,10.0,mx.DAQmx_Val_Volts,None)
        analog_input.CfgSampClkTiming("",10000.0,mx.DAQmx_Val_Rising,mx.DAQmx_Val_FiniteSamps,2)

        # DAQmx Start Code
        analog_input.StartTask()

        # DAQmx Read Code
        analog_input.ReadAnalogF64(1000,10.0,mx.DAQmx_Val_GroupByChannel,data,1000,mx.byref(read),None)
       
        x = data[0]
        return 0 if abs(x) < 1/150 else x # Stupid way to get around crashing at end of execution. If value returned is too small yet still nonzero, program will crash upon completion. Manually found threshold. It's exactly 1/150. No clue why.
        
    def get_internal_chan_old(self, chan):      
        """
        Modifies example of PyDAQmx from https://pythonhosted.org/PyDAQmx/usage.html#task-object . There was a simpler version that I didn't notice before, now that one is implemented above.
        """
        print('start get chan %s' %chan)
        # Declaration of variable passed by reference
        taskHandle = mx.TaskHandle()
        read = mx.int32()
        data = numpy.zeros((1,), dtype=numpy.float64)

        try:
            # DAQmx Configure Code
            mx.DAQmxCreateTask("",mx.byref(taskHandle))
            mx.DAQmxCreateAIVoltageChan(taskHandle,"Dev1/_%s_vs_aognd" %chan,"",mx.DAQmx_Val_Cfg_Default,-10.0,10.0,mx.DAQmx_Val_Volts,None)
            mx.DAQmxCfgSampClkTiming(taskHandle,"",10000.0,mx.DAQmx_Val_Rising,mx.DAQmx_Val_FiniteSamps,2)

            # DAQmx Start Code
            mx.DAQmxStartTask(taskHandle)

            # DAQmx Read Code
            mx.DAQmxReadAnalogF64(taskHandle,1000,10.0,mx.DAQmx_Val_GroupByChannel,data,1000,mx.byref(read),None)

        except mx.DAQError as err:
            print ("DAQmx Error: %s"%err)
        finally:
            if taskHandle:
                # DAQmx Stop Code
                mx.DAQmxStopTask(taskHandle)
                mx.DAQmxClearTask(taskHandle)
        print('end get chan %s' %chan)

        return float(data[0])
        
        
        
if __name__ == '__main__':
    nidaq = NIDAQ()
    
    out_data = []
    in_data = []
    num = 100
    vmax = 5
    for i in range(num):
        nidaq.ao3 = vmax*i/num
        out_data.append(nidaq.ao3)
        in_data.append(nidaq.ai3)
    for i in range(num):
        nidaq.ao3 = vmax-vmax*i/num
        out_data.append(nidaq.ao3)
        in_data.append(nidaq.ai3)
    import matplotlib.pyplot as plt
    plt.plot(in_data)
    plt.show()