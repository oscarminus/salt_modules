# -*- coding: utf-8 -*-
'''
Management of Mailman software
===================================

A state module to manage mailman 

-- Michael Schwarz <schwarz@uni-paderborn.de>

.. code-block:: yaml

'''
from __future__ import absolute_import

# Import python libs
import os
import re
from email.utils import parseaddr

# Import salt libs
import salt.utils

# Some constants, perhaps someone is motivated to convert 
# them into parameters
MM_CONFIG = "/etc/mailman/mm_cfg.py"

def __virtual__():
    '''
    Only load the module if mailman is installed
    '''
    if salt.utils.which('list_lists'):
        return 'mailman'
    return False, 'It seems that mailman is not installed'

############################################################
# Test if list <name> is present and create one if not
############################################################

def list_present(name, **kwargs):
    '''
    Test if list <name> is present and create one if not
    If present, enshure that all intended mebers are subscribed
 
    * name: string
        Name of the list

    * owner: string
        Address of the person who runs the list

    * password: string
        Password of the list.

    * members_present: list
        List of members which should be subscribed

    * members_absend: list
        List of members which should not be subscribed

    * explicit: boolean
        Only members listed in members_present are subscribed on
        this list. Remove all others
    '''

    ret = {'changes': {},
           'comment': 'List %s is in the correct state' % name,
           'name': name,
           'result': True}

    # Test if list is present on this system
    if not __salt__['mailman.list_present'](name):
        if __opts__['test']:
            ret['comment'] = 'List %s is set to be created' % name
            ret['result'] = None
        else:
            if __salt__['mailman.add_list'](name, **kwargs):
                ret['comment'] = 'List %s has been updated' % name
                ret['changes']['Add'] = 'List %s has been created\n' % name
            else:
                # If creation failed, return immedeately
                ret['comment'] = 'Failed to create list %s' % name
                ret['result'] = False
                return ret

    # If test is True and the list would get created, end here
    if not __salt__['mailman.list_present'](name) and __opts__['test']:
        return ret

    # Check password and set
    if 'password' in kwargs:
        if not __salt__['mailman.check_list_password'](name, kwargs['password']):
            if __opts__['test']:
                ret['comment'] = 'List %s is set do be updated' % name
                ret['result'] = None
            else:
                if __salt__['mailman.set_list_password'](name, kwargs['password']):
                    ret['comment'] = 'List %s has been updated' % name
                    ret['changes']['PW'] = 'Password has been changed' 
                else:
                    ret['comment'] = 'Failed to list list %s' % name
                    ret['result'] = False
                    return ret

    # Compare owners
    if 'owner' in kwargs:
        mm_owner = __salt__['mailman.get_owner'](name)
        # ensure salt_owner is a list
        if type(kwargs['owner']) == list:
            salt_owner = kwargs['owner']
        else:
            salt_owner = [kwargs['owner']]

        # Sync owners
        updated = False
        for owner in mm_owner:
            if not owner in salt_owner:
                mm_owner.remove(owner)
                updated = True
        for owner in salt_owner:
            if not owner in mm_owner:
                mm_owner.append(owner)
                updated = True

        if updated:
            if __opts__['test']:
                ret['comment'] = 'List %s is set do be updated' % name
                ret['result'] = None
            else:
                if __salt__['mailman.set_owner'](name, mm_owner):
                    ret['comment'] = 'List %s has been updated' % name
                    ret['changes']['Owner'] = 'Owner has been changed:\n%s' % '\n'.join(mm_owner)
                else:
                    ret['comment'] = 'Failed to list list %s' % name
                    ret['result'] = False
                    return ret
       

    # Check if membership is set correctly
    if 'members_present' in kwargs:
        members_add = []
        for m in kwargs['members_present']:
            # Check if member is already subscribed
            if not __salt__['mailman.is_member'](name, m):
                members_add.append(m)
        if len(members_add) > 0:
            if __opts__['test']:
                ret['comment'] = 'List %s is set do be updated' % name
                ret['result'] = None
                for m in members_add:
                    if 'Subscribed' in ret['changes']:
                        ret['changes']['Subscribed'] = ret['changes']['Subscribed'] + "%s\n" % m
                    else:
                        ret['changes']['Subscribed'] = "%s\n" % m

            else:
                if __salt__['mailman.add_member'](name, members_add):
                    ret['comment'] = 'List %s has been updated' % name
                    for m in members_add:
                        if 'Subscribed' in ret['changes']:
                            ret['changes']['Subscribed'] = ret['changes']['Subscribed'] + "%s\n" % m
                        else:
                            ret['changes']['Subscribed'] = "%s\n" % m
                else:
                    ret['result'] = False
                    ret['comment'] = 'Failed to add new members'
                    return ret

    if 'members_absent' in kwargs:
        members_del = []
        for m in kwargs['members_absent']:
            # Check if member is already subscribed
            if __salt__['mailman.is_member'](name, m):
                members_del.append(m)
        if len(members_del) > 0:
            if __opts__['test']:
                ret['comment'] = 'List %s is set do be updated' % name
                ret['result'] = None
                for m in members_del:
                    if 'Unsubscribed' in ret['changes']:
                        ret['changes']['Unsubscribed'] = ret['changes']['Unsubscribed'] + "%s\n" % m
                    else:
                        ret['changes']['Unsubscribed'] = "%s\n" % m
            else:
                if __salt__['mailman.remove_member'](name, members_del):
                    ret['comment'] = 'List %s has been updated' % name
                    for m in members_del:
                        if 'Unsubscribed' in ret['changes']:
                            ret['changes']['Unsubscribed'] = ret['changes']['Unsubscribed'] + "%s\n" % m
                        else:
                            ret['changes']['Unsubscribed'] = "%s\n" % m
                else:
                    ret['result'] = False
                    ret['comment'] = 'Failed to remove members'
                    return ret

    # if explicit option is set, ensure that only members listet in members_present are subscribed
    if 'explicit' in kwargs:
        mm_list = __salt__['mailman.list_members'](name)

        salt_list = []
        for addr in kwargs['members_present']:
            temp = parseaddr(addr)
            salt_list.append(temp[1])

        del_list = []
        for addr in mm_list:
            if addr not in salt_list:
                del_list.append(addr)

        if len(del_list) > 0:
            if __opts__['test']:
                ret['comment'] = 'List %s is set do be updated' % name
                ret['result'] = None
                for m in del_list:
                    if 'Unsubscribed' in ret['changes']:
                        ret['changes']['Unsubscribed'] = ret['changes']['Unsubscribed'] + "%s (explicit flag)\n" % m
                    else:
                        ret['changes']['Unsubscribed'] = "%s (explicit flag)\n" % m
            else:
                if __salt__['mailman.remove_member'](name, del_list):
                    ret['comment'] = 'List %s has been updated' % name
                    for m in del_list:
                        if 'Unsubscribed' in ret['changes']:
                            ret['changes']['Unsubscribed'] = ret['changes']['Unsubscribed'] + "%s (explicit flag)\n" % m
                        else:
                            ret['changes']['Unsubscribed'] = "%s (explicit flag)\n" % m
                else:
                    ret['result'] = False
                    ret['comment'] = 'Failed to remove members'
                    return ret
               
    return ret 

def list_absent(name):
    '''
    Remove any list named <name>
    '''

    ret = {'changes': {},
           'comment': '',
           'name': name,
           'result': True}

    if __salt__['mailman.list_present'](name):
        if __opts__['test']:
            ret['result'] = None
            ret['comment'] = 'List %s is set so be removed' % name
        else:
            if __salt__['mailman.remove_list'](name):
                ret['comment'] = 'List %s has been removed' % name
            else:
                ret['comment'] = "Couldn't remove list %s" % name
                ret['result'] = False
                return ret
    ret['comment'] = "List %s is absent" % name
    return ret
