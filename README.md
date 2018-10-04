# salt_modules
Saltmodules witten/changed by my own for the purposes of the work at the University of Paderborn

## rbm-lvm.py:
This lvm statemodule supports resizing of logical volumes. For security reasons, only grow is supported.

## mailman.py
The code in `_states` and `_modules` allows to
 * create lists
 * remove lists
 * subscribe members to lists
 * remove memebers from lists
 * and set basic options to a list (owner and passowrd)

If the option `explicit` is set, only members listed in `members_present` will be subscribed to the list.
All other will get removed.
