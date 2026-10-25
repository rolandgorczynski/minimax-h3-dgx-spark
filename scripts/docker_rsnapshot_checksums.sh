#!/bin/sh
# Manueller Job. Startet oder stoppt keine Dienste.
exec /usr/local/sbin/docker-rsnapshot-weekly --verify "$@"
