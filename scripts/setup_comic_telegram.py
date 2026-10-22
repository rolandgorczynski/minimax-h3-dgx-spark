#!/usr/bin/env python3
"""Enter the dedicated bot token privately and discover the permitted chat IDs."""
import getpass
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'automation/comics'))
from telegram_trigger import BotAPI,TelegramError


def main():
    target=ROOT/'automation/comics/.env.telegram'
    if target.exists() and any(line.startswith('TELEGRAM_BOT_TOKEN=') and line.partition('=')[2].strip() for line in target.read_text().splitlines()):
        raise ValueError('Es ist bereits ein Bot-Token hinterlegt. Vorhandene Konfiguration bleibt unverändert.')
    token=getpass.getpass('Token des eigenen Comic-Bots (Eingabe unsichtbar): ').strip()
    api=BotAPI(token);me=api.call('getMe')
    if api.call('getWebhookInfo').get('url'):raise ValueError('Dieser Bot verwendet bereits einen Webhook. Bitte einen eigenen Comic-Bot anlegen.')
    print('Bot: @'+me['username'])
    input('Öffne den Bot in Telegram und sende /start. Danach hier Enter drücken: ')
    updates=api.call('getUpdates',{'timeout':20,'allowed_updates':['message']})
    chats={str(u['message']['chat']['id']) for u in updates if 'message' in u and not u['message'].get('from',{}).get('is_bot')}
    print('Gefundene Chat-IDs: '+(', '.join(sorted(chats)) or 'keine; ID kann manuell eingegeben werden'))
    allowed=input('Erlaubte Chat-ID(s), mehrere mit Komma: ').strip()
    ids=[str(int(value.strip())) for value in allowed.split(',') if value.strip()]
    if not ids:raise ValueError('Mindestens eine Chat-ID ist erforderlich.')
    text='TELEGRAM_BOT_TOKEN='+token+'\nTELEGRAM_ALLOWED_CHAT_IDS='+','.join(ids)+'\nCOMIC_PUBLIC_URL=http://192.168.1.224:8090\n'
    temporary=target.with_suffix('.tmp')
    created=False
    try:
        fd=os.open(temporary,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        created=True
        with os.fdopen(fd,'w') as stream:stream.write(text)
        temporary.replace(target)
    finally:
        if created and temporary.exists():temporary.unlink()
    print('Konfiguration geschützt gespeichert. Aktivieren mit:')
    print('docker compose -p comic-automation -f docker-compose.comic-automation.yml up -d')
    print('Danach /comic 4 noir Ein verlorener Schlüssel an den Bot senden.')


if __name__=='__main__':
    try:main()
    except (ValueError,TelegramError) as exc:print(str(exc),file=sys.stderr);sys.exit(1)
