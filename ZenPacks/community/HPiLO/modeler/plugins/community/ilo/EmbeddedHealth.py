# Twisted Imports
from twisted.internet.defer import inlineCallbacks, returnValue

# Zenoss Imports
from Products.DataCollector.plugins.CollectorPlugin import PythonPlugin
from Products.DataCollector.plugins.DataMaps import RelationshipMap

#Zenpack imports
from ZenPacks.community.HPiLO.lib import hpilo
from ZenPacks.community.HPiLO.utils import  validate_zproperties, read_zenpack_yaml
import yaml
import sys
import os
from pprint import pprint

class EmbeddedHealth(PythonPlugin):

    """HP iLO Embedded Health modeler plugin."""

    requiredProperties = (
        'zManageInterfaceIP',
        'zILoUsername',
        'zILoPassword'
        )

    deviceProperties = PythonPlugin.deviceProperties + requiredProperties

    def prepare_relname(self, s):
        relname = ""
        if len(s) > 0:
            for x,c in enumerate(s):
                if c.islower():
                    relname += s[x:] + 's'
                    break
                else:
                    relname += c.lower()
        return relname

    def get_unit_map(self, unit):
        units_map = {'Percentage':'%',
                     'Celsius':'C'}
        try:
            units_map[unit]
        except KeyError:
            return unit
        return units_map[unit]

    @inlineCallbacks
    def collect(self, device, log):
        """Asynchronously collect data from device. Return a deferred."""
        log.info("%s: collecting data", device.id)

        if validate_zproperties(device) is not True:
            log.error(validate_zproperties(device))

            returnValue(None)

        rm = []

        ilo = hpilo.Ilo(device.zManageInterfaceIP, login=device.zILoUsername, password=device.zILoPassword)

        try:
            fw_version = yield ilo.get_fw_version()
        except Exception, e:
            log.error(
                "%s: %s", device.id, e)

            returnValue(None)

        log.debug("get_fw_version %s:", fw_version)

        try:
            data = yield ilo.get_embedded_health()
        except Exception, e:
            log.error(
                "%s: %s", device.id, e)

            returnValue(None)

        log.debug("get_embedded_health %s:", data)

        try:
            extra_data = yield ilo.get_host_data()
        except Exception, e:
            log.error(
                "%s: %s", device.id, e)

            returnValue(None)

        log.debug("get_host_data %s:", extra_data)

        comp_type_map = {'processors':4,
                         'memory':17,
                         'nic_information':209,
                         'product_name':1}

        if 'processors' not in data.keys():
            data.update({'processors':{}})
            for entry in extra_data:
                if entry['type'] == comp_type_map['processors']:
                    data['processors'].update({entry['Label']:{'execution_technology': entry['Execution Technology']
                                                                                        if 'Execution Technology' in entry else 'N/A',
                                                               'speed': entry['Speed'] if 'Speed' in entry else 'N/A',
                                                               'internal_l1_cache':'N/A',
                                                               'internal_l2_cache':'N/A',
                                                               'internal_l3_cache':'N/A'
                                                               }
                                                })
        if 'memory' not in data.keys():
            data.update({'memory':{}})
            for entry in extra_data:
                if entry['type'] == comp_type_map['memory']:
                    data['memory'].update({entry['Label']:{'memory_speed': entry['Speed'] if 'Speed' in entry else 'N/A',
                                                           'memory_size':entry['Size'],
                                                           }
                                           })
        else:
            if 'memory_components' in data['memory']:
                memory = {}
                for mem in data['memory']['memory_components']:
                    memory.update({mem[0][1]['value']:{'memory_size':mem[1][1]['value'],
                                                       'memory_speed':mem[2][1]['value'],
                                                        }
                                           })
                data['memory'] = memory
            elif 'memory_details' in data['memory']:
                memory = {}
                for k,v in data['memory']['memory_details'].iteritems():
                    for label,mem in v.iteritems():
                        memory.update({"{0} {1}".format(label, k):{'memory_size':mem['size'],
                                                                   'memory_speed':mem['frequency'],
                                                                   }
                                               })
                data['memory'] = memory
            else:
                data.update({'memory':{}})

        if 'nic_information' not in data.keys():
            data.update({'nic_information':{}})
            for entry in extra_data:
                if entry['type'] == comp_type_map['nic_information']:
                    if len(entry['fields']) % 2 != 0 :
                        entry['fields'] = entry['fields'][1:]

                    for i in range(0,len(entry['fields']),2):
                        Label = "{0} {1}".format(entry['fields'][i]['name'], entry['fields'][i]['value'])
                        data['nic_information'].update({Label:{'mac_address':entry['fields'][i+1]['value']}})

        for entry in extra_data: #add system information
            if entry['type'] == comp_type_map['product_name']:
                data['system_information'] = {'model':entry['Product Name'],
                                               'sn':entry['Serial Number'].strip(),
                                               'management_processor':fw_version['management_processor'],
                                               'ilo_fw_version':fw_version['firmware_version'],
                                               'ilo_fw_date':fw_version['firmware_date'],
                                               }

        if 'drives_backplanes' in data.keys():
            data['drive_bays'] = {}
            for backplane in data['drives_backplanes']:
                for k,v in backplane['drive_bays'].iteritems():
                    backplane['drive_bays'][k]['bay'] = k
                    data['drive_bays'].update({'Hard Disk {0}'.format(k):backplane['drive_bays'][k]})

        if 'fans' in data.keys():
            for k,v in data['fans'].iteritems():
                data['fans'][k]['speed'] = "{0}{1}".format(v['speed'][0], self.get_unit_map(v['speed'][1]))

        if 'vrm' in data and data['vrm'] is None:
            data['vrm'] = {}

        if 'temperature' in data.keys():
            for k,v in data['temperature'].iteritems():
                data['temperature'][k]['currentreading'] = "{0} {1}".format(v['currentreading'][0],
                                                                            self.get_unit_map(v['currentreading'][1]))
                data['temperature'][k]['caution'] = "{0} {1}".format(v['caution'][0], self.get_unit_map(v['caution'][1]))
                data['temperature'][k]['critical'] = "{0} {1}".format(v['critical'][0], self.get_unit_map(v['critical'][1]))

        zenpack_yaml = read_zenpack_yaml('ZenPacks.community.HPiLO')
        if type(zenpack_yaml).__name__ != 'dict':
            log.error(zenpack_yaml)

            returnValue(None)

        comp_map = {}
        for comp_class, comp in zenpack_yaml['classes'].iteritems():
            comp_map[comp['plural_short_label']] = {'properties':comp['properties'].keys(),
                                                    'class':comp_class
                                                    }

        for comp_type in data.keys():
            if comp_type in comp_map.keys():
                comp_list = []
                for k,v in data[comp_type].iteritems():
                    comp = {'id':self.prepId(k.replace (" ", "_")),
                            'title':k}
                    for property in comp_map[comp_type]['properties']:
                        comp[property] = v[property]
                    comp_list.append(self.objectMap(comp))

                rm.append(RelationshipMap(
                    relname=self.prepare_relname(comp_map[comp_type]['class']),
                    modname='ZenPacks.community.HPiLO.{0}'.format(comp_map[comp_type]['class']),
                    objmaps=comp_list,
                ))

        rm.append(self.objectMap({'setHWSerialNumber':data['system_information']['sn'],
                                  'setHWProductKey':data['system_information']['model'],
                                  'setHWTag':data['system_information']['ilo_fw_version']}))
        returnValue(rm)

    def process(self, device, results, log):
        """Process results. Return iterable of datamaps or None."""
        return results