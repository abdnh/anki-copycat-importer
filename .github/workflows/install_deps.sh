#!/usr/bin/env bash

pip install uv
uv sync
sudo apt-get update
sudo apt install libxcb-xinerama0 libxcb-cursor0 libegl1
curl -fsSL https://dprint.dev/install.sh | sh -s > /dev/null 2>&1
echo "$HOME/.dprint/bin" >> $GITHUB_PATH
