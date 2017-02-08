======================================
ZenPacks.community.HPiLO
======================================


Description
===========

This ZenPack perform monitoring of HP server hardware with HPiLO(Integrated Lights-Out).
Components provides:
-  Temperature Sensors
-  Ports
-  Memory Modules
-  Power Supplies
-  Hard Disks
-  Fans
-  VRMs
-  Processors

Monitoring only checks status of components, no performance information available.

Requirements & Dependencies
===========================

    * Zenoss Versions Supported: > 4.0
    * External Dependencies:
    * ZenPack Dependencies:
    * Installation Notes: zenhub and zopectl restart after installing this ZenPack.
    * Configuration:

Installation
============
Normal Installation (packaged egg)
----------------------------------
Copy the downloaded .egg to your Zenoss server and run the following commands as the zenoss
user::

   * zenpack --install <package.egg>
   * zenhub restart
   * zopectl restart

Developer Installation (link mode)
----------------------------------
If you wish to further develop and possibly contribute back to this
ZenPack you should clone the git repository, then install the ZenPack in
developer mode::

   * zenpack --link --install <package>
   * zenhub restart
   * zopectl restart

Configuration
=============

Tested with Zenoss 4.2.5

zProperties
-----------
- **zManageInterfaceIP** - ip address of management interface
- **zILoUsername** - username to use for login
- **zILoPassword** - password to use for login 

Monitoring Templates
-----------
- ** /Devices/Server/rrdTemplates/HPiLOEvents**

Event Classes
-----------
- **/Status/HPiLO**

Screenshots
===========
* |HPiLODeviceOverview.png|
