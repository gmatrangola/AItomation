#!/bin/bash

# Run the Home Assistant container
docker run -d \
  --name homeassistant \
  -v ~/ha-config:/config \
  -p 8123:8123 \
  --restart=unless-stopped \
  ghcr.io/home-assistant/home-assistant:stable