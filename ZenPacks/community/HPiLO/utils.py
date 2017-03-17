#Zenpack imports
import yaml
import sys
import os
from ZenPacks.community.HPiLO.lib import hpilo

import logging
log = logging.getLogger('zen.HPiLO')

def validate_zproperties(obj):
    """ check all required zproperties is set """
    required_zproperties = ['zManageInterfaceIP', 'zILoUsername', 'zILoPassword']

    for zproperty in required_zproperties:
        zvalue = getattr(obj, zproperty, None)
        if not zvalue:
            return "%s: %s not set.", obj.id, zproperty
    return True

def read_zenpack_yaml(zenpack_module):
    """ read content of yaml file in dict
    zenpack_module(str)
    """
    zenpack_yaml_path = os.path.dirname(sys.modules[zenpack_module].__file__)
    with open("{0}/zenpack.yaml".format(zenpack_yaml_path), 'r') as stream:
        try:
            zenpack_yaml = yaml.load(stream)
        except yaml.YAMLError as exc:
            return "%s: %s", config.id, exc
    return zenpack_yaml

def prepare_relname(s):
    relname = ""
    if len(s) > 0:
        for x,c in enumerate(s):
            if c.islower():
                relname += s[x:] + 's'
                break
            else:
                relname += c.lower()
    return relname

def get_unit_map(unit):
    units_map = {'Percentage':'%',
                 'Celsius':'C'}
    try:
        units_map[unit]
    except KeyError:
        return unit
    return units_map[unit]

def get_ilo_data(ILoInterfaceIP, ILoUsername, ILoPassword):
    """ query data from iLo and change returned format to appropriate modeling and monitoring methods data format """
    ilo = hpilo.Ilo(ILoInterfaceIP, login=ILoUsername, password=ILoPassword)

    try:
        fw_version = ilo.get_fw_version()
    except Exception, e:
        return "%s: %s", device.id, e

    log.debug("get_fw_version %s:", fw_version)

    try:
        data = ilo.get_embedded_health()
    except Exception, e:
        return "%s: %s", device.id, e

    log.debug("get_embedded_health %s:", data)

    try:
        extra_data = ilo.get_host_data()
    except Exception, e:
        return "%s: %s", device.id, e

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
                backplane['drive_bays'][k]['bay'] = 'Bay {0}'.format(k)
                data['drive_bays'].update({'Hard Disk {0}'.format(k):backplane['drive_bays'][k]})

    if 'storage' in data.keys():
        data['drive_bays'] = {}
        hdd_count = 0
        for enclosure in data['storage']:
            if 'logical_drives' in data['storage'][enclosure].keys():
                for logical_drive in data['storage'][enclosure]['logical_drives']:
                    for hdd in logical_drive['physical_drives']:
                        hdd_count += 1
                        hdd['product_id'] = hdd['serial_number']
                        hdd['bay'] = hdd['location']
                        data['drive_bays'].update({'Hard Disk {0}'.format(hdd_count):hdd})

    if 'fans' in data.keys():
        for k,v in data['fans'].iteritems():
            data['fans'][k]['speed'] = "{0}{1}".format(v['speed'][0], get_unit_map(v['speed'][1]))

    if 'vrm' in data and data['vrm'] is None:
        data['vrm'] = {}

    if 'temperature' in data.keys():
        for k,v in data['temperature'].iteritems():
            data['temperature'][k]['currentreading'] = "{0} {1}".format(v['currentreading'][0],
                                                                        get_unit_map(v['currentreading'][1]))
            data['temperature'][k]['caution'] = "{0} {1}".format(v['caution'][0], get_unit_map(v['caution'][1]))
            data['temperature'][k]['critical'] = "{0} {1}".format(v['critical'][0], get_unit_map(v['critical'][1]))

    return data