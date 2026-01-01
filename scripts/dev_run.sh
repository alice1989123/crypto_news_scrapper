#!/usr/bin/env bash
set -euo pipefail

# run with virtual framebuffer (headless firefox)
xvfb-run -a python3 scraper.py
