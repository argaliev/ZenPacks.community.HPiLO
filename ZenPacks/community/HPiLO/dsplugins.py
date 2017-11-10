# Twisted Imports
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread

# Zenoss Imports
from ZenPacks.zenoss.PythonCollector.datasources.PythonDataSource import PythonDataSourcePlugin
from Products.ZenEvents.ZenEventClasses import Warning, Error, Critical, Clear

#Zenpack imports
from ZenPacks.community.HPiLO.utils import  validate_zproperties, read_zenpack_yaml, get_ilo_data
from pprint import pprint

import logging
log = logging.getLogger('zen.HPiLO')

class Events(PythonDataSourcePlugin):

    proxy_attributes = (
        'zManageInterfaceIP',
        'zILoUsername',
        'zILoPassword'
        )

    @classmethod
    def config_key(cls, datasource, context):
        return (
            context.device().id,
            datasource.getCycleTime(context),
            datasource.rrdTemplate().id,
            datasource.id,
            datasource.plugin_classname,
            )

    @classmethod
    def params(cls, datasource, context):
        params = {}
        log.debug(' params is {0}'.format(params))
        return params

    @inlineCallbacks
    def collect(self, config):
        ds0 = config.datasources[0]
        data = self.new_data()

        if validate_zproperties(ds0) is not True:
            log.error("{0}: {1}".format(config.id, validate_zproperties(ds0)))
            
            data['events'].append({
                                'device': config.id,
                                'severity': ds0.severity,
                                'eventKey': 'validate_zproperties',
                                'eventClass': ds0.eventClass,
                                'summary': str(validate_zproperties(ds0)),
                            })

            returnValue(data)
        else:
            data['events'].append({
                                'device': config.id,
                                'severity': Clear,
                                'eventKey': 'validate_zproperties',
                                'eventClass': ds0.eventClass,
                                'summary': 'validate_zproperties is OK',
                            })

        ilo_data = yield deferToThread(get_ilo_data, ds0.zManageInterfaceIP, ds0.zILoUsername, ds0.zILoPassword)

        if type(ilo_data).__name__ != 'dict':
            log.error("{0}: {1}".format(config.id, ilo_data))
            
            data['events'].append({
                                'device': config.id,
                                'severity': ds0.severity,
                                'eventKey': 'get_ilo_data',
                                'eventClass': ds0.eventClass,
                                'summary': str(ilo_data),
                            })

            returnValue(data)
        else:
            data['events'].append({
                                'device': config.id,
                                'severity': Clear,
                                'eventKey': 'get_ilo_data',
                                'eventClass': ds0.eventClass,
                                'summary': 'get_ilo_data is OK',
                            })

        zenpack_yaml = read_zenpack_yaml('ZenPacks.community.HPiLO')
        if type(zenpack_yaml).__name__ != 'dict':
            log.error("{0}: {1}".format(config.id, zenpack_yaml))
            
            data['events'].append({
                                'device': config.id,
                                'severity': ds0.severity,
                                'eventKey': 'read_zenpack_yaml',
                                'eventClass': ds0.eventClass,
                                'summary': str(zenpack_yaml),
                            })

            returnValue(data)
        else:
            data['events'].append({
                                'device': config.id,
                                'severity': Clear,
                                'eventKey': 'read_zenpack_yaml',
                                'eventClass': ds0.eventClass,
                                'summary': 'read_zenpack_yaml is OK',
                            })

        status_comps = []
        for comp_class, comp in zenpack_yaml['classes'].iteritems():
            if 'status' in comp['properties'].keys():
                status_comps.append(comp['plural_short_label'])

        log.debug("status_comps: {0}".format(status_comps))

        for comp_type in ilo_data.keys():
            if comp_type in status_comps:
                if ilo_data[comp_type]:
                    for k,v in ilo_data[comp_type].iteritems():
                        comp_id = k.replace(" ","_")
                        if v['status'].lower() not in ['ok','n/a','good, in use','not installed']:
                            data['events'].append({
                                        'device': config.id,
                                        'severity': ds0.severity,
                                        'component':comp_id,
                                        'eventKey': '{0}_status'.format(comp_id),
                                        'eventClass': ds0.eventClass,
                                        'summary': '{0} current status: {1}'.format(k, v['status']),
                                    })
                        else:
                            data['events'].append({
                                        'device': config.id,
                                        'severity': Clear,
                                        'component':comp_id,
                                        'eventKey': '{0}_status'.format(comp_id),
                                        'eventClass': ds0.eventClass,
                                        'summary': '{0} status: ok'.format(k),
                                    })

        log.debug( 'data is {0}'.format(data))
        returnValue(data)