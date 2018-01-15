import os
from ZenPacks.zenoss.ZenPackLib import zenpacklib

CFG = zenpacklib.load_yaml([os.path.join(os.path.dirname(__file__), "zenpack.yaml")], verbose=False, level=30)
schema = CFG.zenpack_module.schema

import Globals

from Products.ZenModel.ZenPack import ZenPack as ZenPackBase
from Products.ZenUtils.Utils import unused
from Products.Zuul import getFacade
from transaction import commit

unused(Globals)

def DeleteComponentsByType(devices, type):
   df = getFacade('device')
   for d in devices.getSubDevices():
      components = df.getComponents(d.getPrimaryId(), meta_type=type)
      if components.total > 0:
         del_list = []
         for brain in components:
            del_list.append(brain.uid)
         try:
            df.deleteComponents(del_list)
         except:
            print "Error on %s" % d.getPrimaryId()
         print "Removing {0}: {1}".format(type, del_list)
         commit()

class ZenPack(ZenPackBase):
    def install(self, app):
        """Custom install method for this ZenPack."""
        self.pre_install(app)
        super(ZenPack, self).install(app)

    def pre_install(self, app):
        """Perform steps that should be done before default install."""
        """Cleanup components that may occur problems with old relations """
        
        devices = app.zport.dmd.Devices
        
        print "Removing old components relations"
        DeleteComponentsByType(devices, 'ILoProcessor')
        DeleteComponentsByType(devices, 'ILoTemperature')
        DeleteComponentsByType(devices, 'ILoPowerSupply')