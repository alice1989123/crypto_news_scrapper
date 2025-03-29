FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    wget curl ca-certificates \
    python3 python3-pip \
    xvfb \
    libgtk-3-0 libdbus-glib-1-2 libasound2 libx11-xcb1 \
    libxcomposite1 libxdamage1 libxrandr2 libgbm1 libnss3 libxss1 \
    libatk-bridge2.0-0 libatk1.0-0 libdrm2 \
    && rm -rf /var/lib/apt/lists/*

# Install real Firefox from Mozilla (no snap)
RUN mkdir -p /opt/firefox && \
    wget -O /tmp/firefox.tar.bz2 "https://ftp.mozilla.org/pub/firefox/releases/124.0.2/linux-x86_64/en-US/firefox-124.0.2.tar.bz2" && \
    tar -xjf /tmp/firefox.tar.bz2 -C /opt/firefox --strip-components=1 && \
    ln -s /opt/firefox/firefox /usr/bin/firefox && \
    rm /tmp/firefox.tar.bz2

# Set working directory
WORKDIR /app

# Copy geckodriver manually (your binary)
COPY geckodriver /usr/local/bin/geckodriver
RUN chmod +x /usr/local/bin/geckodriver

# Copy scraper script
COPY scraper.py .

# Install Python dependencies
RUN pip3 install selenium beautifulsoup4

# Run the script inside a virtual framebuffer
CMD ["xvfb-run", "-a", "python3", "scraper.py"]
