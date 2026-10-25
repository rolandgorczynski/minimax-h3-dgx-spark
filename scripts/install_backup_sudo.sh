#!/bin/bash
# Installiert nur die Leseberechtigung; startet keine Sicherung.
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "Bitte einmal mit sudo ausführen." >&2; exit 1; }
account=${SUDO_USER:-jee}
[[ "$account" =~ ^[a-z_][a-z0-9_-]*$ ]] || exit 1
id "$account" >/dev/null
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
cat > "$scratch/helper" <<'HELPER'
#!/usr/bin/python3 -I
"""Ausschließlich Ollama-Modelle als Archiv nach stdout lesen."""
import os
import sys
if len(sys.argv) != 1:
    sys.exit("Keine Argumente erlaubt.")
os.execve('/usr/bin/tar', ['tar', '--numeric-owner', '--acls', '--xattrs',
    '--exclude=.git', '--exclude=*/.git', '--exclude=__pycache__',
    '--exclude=*/__pycache__', '-cpf', '-',
    '-C', '/usr/share/ollama/.ollama/models', '.'],
    {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'})
HELPER
printf '%s ALL=(root) NOPASSWD: /usr/local/sbin/comic-backup-ollama ""\n' "$account" > "$scratch/rule"
/usr/sbin/visudo -cf "$scratch/rule"
install -o root -g root -m 0755 "$scratch/helper" /usr/local/sbin/comic-backup-ollama
install -o root -g root -m 0440 "$scratch/rule" /etc/sudoers.d/comic-backup-ollama
echo "Dauerhafte Backup-Leseberechtigung eingerichtet. Keine Sicherung gestartet."
