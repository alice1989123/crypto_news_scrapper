#!/bin/bash
set -e

echo "🟢  $(date '+%F %T') – pod started"            # 1) early heartbeat
stdbuf -oL -eL xvfb-run -a -s "-screen 0 1024x768x24" \
        python3 /app/scraper.py
echo "✅  $(date '+%F %T') – scraper finished"