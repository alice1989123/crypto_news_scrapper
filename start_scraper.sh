#!/bin/bash
set -e

echo "🟢  $(date '+%F %T') – pod started"

logfile="/app/scraper.log"

stdbuf -oL -eL xvfb-run -a -s "-screen 0 1024x768x24" \
    python3 /app/scraper.py 2>&1 | tee "$logfile"

echo "✅  $(date '+%F %T') – scraper finished"
