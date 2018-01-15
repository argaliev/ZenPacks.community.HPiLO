# Twisted Imports
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread

# Zenoss Imports
from Products.DataCollector.plugins.CollectorPlugin import PythonPlugin
from Products.DataCollector.plugins.DataMaps import RelationshipMap

#Zenpack imports
from ZenPacks.community.HPiLO.utils import  validate_zproperties, read_zenpack_yaml, prepare_relname, get_ilo_data
from pprint import pprint

class EmbeddedHealth(PythonPlugin):

    """HP iLO Embedded Health modeler plugin."""

    requiredProperties = (
        'zManageInterfaceIP',
        'zILoUsername',
        'zILoPassword'
        )

    deviceProperties = PythonPlugin.deviceProperties + requiredProperties

    @inlineCallbacks
    def collect(self, device, log):
        """Asynchronously collect data from device. Return a deferred."""
        log.info("{0}: collecting data".format(device.id))

        if validate_zproperties(device) is not True:
            log.error("{0}: {1}".format(device.id, validate_zproperties(device)))

            returnValue(None)

        rm = []

        data = yield deferToThread(get_ilo_data, device.zManageInterfaceIP, device.zILoUsername, device.zILoPassword)

        if type(data).__name__ != 'dict':
            log.error("{0}: {1}".format(device.id, data))

            returnValue(None)

        zenpack_yaml = read_zenpack_yaml('ZenPacks.community.HPiLO')
        if type(zenpack_yaml).__name__ != 'dict':
            log.error("{0}: {1}".format(device.id, zenpack_yaml))

            returnValue(None)

        zenoss_compname_map = {'processors':'cpus',
                               'power_supplies':'powersupplies',
                               'temperature':'temperaturesensors',
                               }
        
        comp_map = {}
        for comp_class, comp in zenpack_yaml['classes'].iteritems():
            comp_map[comp['plural_short_label']] = {'properties': comp['properties'].keys(),
                                                    'class': comp_class,
                                                    'relname': zenoss_compname_map.get(comp['plural_short_label'],None) or prepare_relname(comp_class),
                                                    'compname': 'hw' if comp['plural_short_label'] in zenoss_compname_map else ''
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
                
                log.debug(comp_map[comp_type])
                rm.append(RelationshipMap(
                    compname=comp_map[comp_type]['compname'],
                    relname=comp_map[comp_type]['relname'],
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