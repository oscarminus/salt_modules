#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This module is intended to configure the mailman email list software
# 
# -- Michael Schwarz <schwarz@math.uni-paderborn.de>
#    October 2018

from __future__ import absolute_import

import sys, os
import subprocess
import re
import tempfile
from email.utils import parseaddr

# Some constants
MM_PATH = "/var/lib/mailman/bin"
DEFAULT_OWNER = "root@localhost.localdomain"


# Try to import Mailman helper, otherwise exit
try:
    sys.path.append(MM_PATH)
    import paths
    from Mailman import mm_cfg
    from Mailman import Utils
    from Mailman import MailList
except ImportError:
    sys.exit(1)

# This function is called by salt to check if this module is operational
def __virtual__():
    if subprocess.call(['which', 'list_members'], stdout=subprocess.PIPE) == 0:
        return 'mailman'
    else:
        return False, 'It seems, that mailman is not installed'

############################################################################
# Public functions
############################################################################

# Check if list is present
def list_present(name):
    return Utils.list_exists(name.lower())

# Add a list
def add_list(name, **kwargs):
    '''
    Adds a list to the server

    Arguments:
     - name: The desired name of the list
     - owner: The owner of the list. If not set, root@localhost.localdomain is used
     - password: A given password for the list. If empty, a random password will be set.
     - language: Language of list (optional)
     - urlhost: Urlhost of the list (optional)
     - emailhost: Run list under other email-domain (optional)

    Returns true or false
    '''

    # If list is already present, exit
    if list_present(name):
        return False, 'List is already present on this system'

    owner = DEFAULT_OWNER
    if 'owner' in kwargs:
        owner = kwargs['owner']

    if 'password' in kwargs:
        password = kwargs['password']
    else:
        password = Utils.MakeRandomPassword(
                mm_cfg.ADMIN_PASSWORD_LENGTH)
    
    # Add optional arguments
    args = ''
    if 'language' in kwargs:
        args = args + " -l %s" % kwargs['language']

    if 'urlhost' in kwargs:
        args = args + " -u %s" % kwargs['urlhost']

    if 'emailhost' in kwargs:
        args = args + " -e %s" % kwargs['emailhost']
    
    # We use the commandline tools, because they do a lot of checks,
    # we don't want to reimplement all of them.
    if len(args) > 0:
        cmdline = "%s/newlist %s %s %s %s" % (MM_PATH, args.strip(), name, owner, password)
    else:
        cmdline = "%s/newlist %s %s %s" % (MM_PATH, name, owner, password)

    cmd = cmdline.split(' ')
    p = subprocess.Popen(cmd,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE)
    p.communicate('\n')
    p.wait()
    if p.returncode == 0:
        return True
    return False, 'Could not add list %s, something went wrong' % name

# Remove a list
def remove_list(name, archives=True):
    '''
    Remove list from the system

    Arguments:
     - name: Name of the list to remove
     - archives: Remove archive too, defaults to true

    Returns true or false
    '''

    # If list doesn't exist, do nothing and exit
    if not list_present(name):
        return True

    if archives:
        cmd = ['%s/rmlist' % MM_PATH, '-a', name]
    else:
        cmd = ['%s/rmlist' % MM_PATH, name]

    p = subprocess.Popen(cmd,
            stdout=subprocess.PIPE)
    p.wait()
    if p.returncode == 0:
        return True
    return False, 'Removal of list %s failed' % name


# List members
def list_members(name, fullnames=False):
    # If list <name> doesn't exist, exit
    if not list_present(name):
        return False, 'List is not present on this system'

    members = []
    if fullnames:
        cmd = [ '%s/list_members' % MM_PATH, '-f', name ]
    else:
        cmd = [ '%s/list_members' % MM_PATH, name ]
    p = subprocess.Popen(cmd,
            stdout=subprocess.PIPE)
    p.wait()
    if p.returncode == 0:
        for line in p.stdout:
            members.append(line.strip())
        return members
    return False

# Check if email address is member of a list
def is_member(name, email):
    # If list <name> doesn't exist, exit
    if not list_present(name):
        return False, 'List is not present on this system'

    email = parseaddr(email)

    cmd = [ '%s/list_members' % MM_PATH, name ]
    p = subprocess.Popen(cmd,
            stdout=subprocess.PIPE)
    p.wait()
    if p.returncode == 0:
        for line in p.stdout:
            if re.match("^"+email[1]+"$", line):
                return True
    return False

# Add memebers to the list
def add_member(name, members):
    '''
    Add a member to the list

    Arguments:
     - name: Name of the list
     - members: Members to add, should be a list

    Notification of the new members will be handled according to the default
    settings of the list itself.

    Returns true or false
    '''

    if not list_present(name):
        return False, 'List is not present on this system'

    # if members is not a list, encapsulate it as a list
    if not type(members) == list:
        members = [ members ]

    cmd = ['%s/add_members' % MM_PATH, '-r', '-', name]
    p = subprocess.Popen(cmd,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE)
    p.communicate('\n'.join(members))
    p.wait()
    if p.returncode == 0:
        return True
    return False, 'Could not add members to list %s, somethin went wrong' % name

# Remove members from the list
def remove_member(name, members):
    '''
    Remove members from the list

    Arguments:
     - name: Name of the list
     - members: Members to remove, should be a list

    Notification of the old members will be handled according to the default
    settings of the list itself.

    Returns true or false
    '''

    if not list_present(name):
        return False, 'List is not present on this system'

    # if members is not a list, encapsulate it as a list
    if not type(members) == list:
        members = [ members ]

    # Strip fullnames in Mailadresses
    del_members = []
    for m in members:
        m_tuple = parseaddr(m)
        del_members.append(m_tuple[1])

    cmd = ['%s/remove_members' % MM_PATH, '-f', '-', name]
    p = subprocess.Popen(cmd,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE)
    p.communicate('\n'.join(del_members))
    p.wait()
    if p.returncode == 0:
        return True
    return False, 'Removal of members on list %s failed' % name

def get_owner(name):
    '''
    Get the email address of the person who runs this list
    '''

    l = MailList.MailList(name.lower(), lock=0)
    return l.owner

def set_owner(name, owner):
    '''
    Set the mail address of the person who runs the list.

    Mailman supports a set of owners. 
    '''

    if not type(owner) == list:
        owner = [owner]

    l = MailList.MailList(name.lower())
    try:
        l.owner = owner
        l.Save()
    finally:
        l.Unlock()
    return True


def set_list_password(name, password):
    '''
    Set the list admin password
    '''

    l = MailList.MailList(name.lower(), lock=0)
    if len(password) < 1:
        return False, 'Empty passwords are not allowed'
    shapassword = Utils.sha_new(password).hexdigest()
    l.Lock()
    try:
        l.password = shapassword
        l.Save()
    finally:
        l.Unlock()
    return True

def check_list_password(name, password):
    '''
    Test if password matches the admin password for this list.  
    '''
    l = MailList.MailList(name.lower(), lock=0)
    auth = l.Authenticate([mm_cfg.AuthListAdmin], password)
    if auth == mm_cfg.UnAuthorized:
        return False
    return True
