#!/bin/bash

# Syncs code from the main dev branch to HACS repo.
cd ~/projects/homeassistant/rointe-hacs/custom_components/rointe
rsync -av --prune-empty-dirs --include '*/' --include='*.py'  --include='*.json' --exclude='*'   ~/projects/homeassistant/core/homeassistant/components/rointe/* .

echo "Code synchronized."

