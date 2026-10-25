#!/bin/bash
# Switch back to headless (no visible desktop).
systemctl --user stop weston-waydroid.service
systemctl --user start weston-headless.service
systemctl --user is-active weston-headless.service
