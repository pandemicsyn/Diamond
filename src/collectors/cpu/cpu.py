# coding=utf-8

"""
The CPUCollector collects CPU utilization metric using /proc/stat.

#### Dependencies

 * /proc/stat

"""

import diamond.collector
import os

try:
    import psutil
    psutil  # workaround for pyflakes issue #13
except ImportError:
    psutil = None


class CPUCollector(diamond.collector.Collector):

    PROC = '/proc/stat'
    MAX_VALUES = {
        'user': diamond.collector.MAX_COUNTER,
        'nice': diamond.collector.MAX_COUNTER,
        'system': diamond.collector.MAX_COUNTER,
        'idle': diamond.collector.MAX_COUNTER,
        'iowait': diamond.collector.MAX_COUNTER,
        'irq': diamond.collector.MAX_COUNTER,
        'softirq': diamond.collector.MAX_COUNTER,
        'steal': diamond.collector.MAX_COUNTER,
        'guest': diamond.collector.MAX_COUNTER,
        'guest_nice': diamond.collector.MAX_COUNTER,
    }

    def get_default_config_help(self):
        config_help = super(CPUCollector, self).get_default_config_help()
        config_help.update({
        })
        return config_help

    def get_default_config(self):
        """
        Returns the default collector settings
        """
        config = super(CPUCollector, self).get_default_config()
        config.update({
            'enabled':  'True',
            'path':     'cpu',
            'xenfix':   None,
        })
        return config

    def collect(self):
        """
        Collector cpu stats
        """
        if os.access(self.PROC, os.R_OK):

            results = {}
            # Open file
            file = open(self.PROC)

            for line in file:
                if not line.startswith('cpu'):
                    continue

                elements = line.split()

                cpu = elements[0]

                if cpu == 'cpu':
                    cpu = 'total'

                results[cpu] = {}

                if len(elements) >= 2:
                    results[cpu]['user'] = elements[1]
                if len(elements) >= 3:
                    results[cpu]['nice'] = elements[2]
                if len(elements) >= 4:
                    results[cpu]['system'] = elements[3]
                if len(elements) >= 5:
                    results[cpu]['idle'] = elements[4]
                if len(elements) >= 6:
                    results[cpu]['iowait'] = elements[5]
                if len(elements) >= 7:
                    results[cpu]['irq'] = elements[6]
                if len(elements) >= 8:
                    results[cpu]['softirq'] = elements[7]
                if len(elements) >= 9:
                    results[cpu]['steal'] = elements[8]
                if len(elements) >= 10:
                    results[cpu]['guest'] = elements[9]
                if len(elements) >= 11:
                    results[cpu]['guest_nice'] = elements[10]

            # Close File
            file.close()

            metrics = {}

            for cpu in results.keys():
                stats = results[cpu]
                for s in stats.keys():
                    # Get Metric Name
                    metric_name = '.'.join([cpu, s])
                    # Get actual data
                    metrics[metric_name] = self.derivative(metric_name,
                                                         long(stats[s]),
                                                         self.MAX_VALUES[s])

            # Check for a bug in xen where the idle time is doubled for guest
            # See https://bugzilla.redhat.com/show_bug.cgi?id=624756
            if self.config['xenfix'] is None or self.config['xenfix'] == True:
                if os.path.isdir('/proc/xen'):
                    total = 0
                    for metric_name in metrics.keys():
                        if 'cpu0.' in metric_name:
                            total += int(metrics[metric_name])
                    if total > 110:
                        self.config['xenfix'] = True
                        for mname in metrics.keys():
                            if '.idle' in mname:
                                metrics[mname] = float(metrics[mname]) / 2
                    elif total > 0:
                        self.config['xenfix'] = False
                else:
                    self.config['xenfix'] = False

            # Publish Metric Derivative
            for metric_name in metrics.keys():
                self.publish(metric_name,
                             metrics[metric_name])
            return True

        elif psutil:
            cpu_time = psutil.cpu_times(True)
            total_time = psutil.cpu_times()
            for i in range(0, len(cpu_time)):
                metric_name = 'cpu' + str(i)
                self.publish(metric_name + '.user',
                             self.derivative(metric_name + '.user',
                                             cpu_time[i].user,
                                             self.MAX_VALUES['user']))
                self.publish(metric_name + '.nice',
                             self.derivative(metric_name + '.nice',
                                             cpu_time[i].nice,
                                             self.MAX_VALUES['nice']))
                self.publish(metric_name + '.system',
                             self.derivative(metric_name + '.system',
                                             cpu_time[i].system,
                                             self.MAX_VALUES['system']))
                self.publish(metric_name + '.idle',
                             self.derivative(metric_name + '.idle',
                                             cpu_time[i].idle,
                                             self.MAX_VALUES['idle']))

            metric_name = 'total'
            self.publish(metric_name + '.user',
                         self.derivative(metric_name + '.user',
                                         total_time.user,
                                         self.MAX_VALUES['user']))
            self.publish(metric_name + '.nice',
                         self.derivative(metric_name + '.nice',
                                         total_time.nice,
                                         self.MAX_VALUES['nice']))
            self.publish(metric_name + '.system',
                         self.derivative(metric_name + '.system',
                                         total_time.system,
                                         self.MAX_VALUES['system']))
            self.publish(metric_name + '.idle',
                         self.derivative(metric_name + '.idle',
                                         total_time.idle,
                                         self.MAX_VALUES['idle']))

            return True

        return None
