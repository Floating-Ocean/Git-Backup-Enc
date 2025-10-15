#!/bin/bash
# Example cron job script for automated backups
# This script can be used in cron to perform scheduled backups

# Set the working directory to where your backup scripts are located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Set password from environment or pass as argument
export BACKUP_PASSWORD="${BACKUP_PASSWORD:-$1}"

# Run backup
python3 backup.py -c config.yaml

# Optional: Log the result
echo "Backup completed at $(date)" >> backup.log
