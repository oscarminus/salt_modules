mailman:
  pkg.installed: []
  service.running:
    - enable: True
    - restart: True

/etc/mailman/mm_cfg.py:
  file.managed:
    - source: salt://mailserver/mailman/mm_cfg
    - watch_in:
      - service: mailman

Intern:
  mailman.list_present:
    # Only members listed under members_present are subscribed to this list
    - explicit: True
    - owner: 'postmaster@math.uni-paderborn.de'
    - members_present:
{% for admin in pillar['admins'] %}
      - {{pillar['admins'][admin]['email']}}
{% endfor %}
