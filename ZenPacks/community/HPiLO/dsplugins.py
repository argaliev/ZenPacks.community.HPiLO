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
        log.debug(' params is %s \n' % (params))
        return params

    @inlineCallbacks
    def collect(self, config):
        ds0 = config.datasources[0]
        data = self.new_data()

        if validate_zproperties(ds0) is not True:
            log.error(validate_zproperties(ds0))

            returnValue(None)

        ilo_data = yield deferToThread(get_ilo_data, ds0.zManageInterfaceIP, ds0.zILoUsername, ds0.zILoPassword)

        if type(ilo_data).__name__ != 'dict':
            log.error(ilo_data)

            returnValue(None)

        zenpack_yaml = read_zenpack_yaml('ZenPacks.community.HPiLO')
        if type(zenpack_yaml).__name__ != 'dict':
            log.error(zenpack_yaml)

            returnValue(None)

        status_comps = []
        for comp_class, comp in zenpack_yaml['classes'].iteritems():
            if 'status' in comp['properties'].keys():
                status_comps.append(comp['plural_short_label'])

        log.debug("status_comps %s:", status_comps)

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

        log.debug( 'data is %s ' % (data))
        returnValue(data)