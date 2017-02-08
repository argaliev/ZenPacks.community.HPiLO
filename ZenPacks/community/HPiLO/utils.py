#Zenpack imports
import yaml
import sys
import os

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