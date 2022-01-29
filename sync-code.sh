#!/bin/bash

# Syncs code from the main dev branch to HACS repo.
cd /workspaces/rointe-hacs/custom_components/rointe
rsync -av --prune-empty-dirs --include '*/' --exclude='manifest.json' --include='*.py'  --include='*.json' --exclude='*'   /workspaces/core/homeassistant/components/rointe/* .


echo "Update Versions!"