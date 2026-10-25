#!/bin/bash
set +e
sudo -n lxc-attach -P /var/lib/waydroid/lxc -n waydroid -- sh -c '
  ls /data/local/tmp/cacerts | wc -l
  cat /data/local/tmp/hosts
  mount --bind /data/local/tmp/cacerts /system/etc/security/cacerts
  mount --bind /data/local/tmp/hosts /system/etc/hosts
  echo "--- after ---"
  cat /system/etc/hosts
  ls /system/etc/security/cacerts | wc -l
'
