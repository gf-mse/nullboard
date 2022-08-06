#!/bin/bash

app='./nullboard_backup_srv.py'
savedir='nullboard-backups'
mkdir -p $savedir

port=20002
debug=1

# // comment it out if not used
# token='12345'

DEBUG=$debug BACKUP_DIR="$savedir" PORT=$port ACCESS_TOKEN="$token" $app

