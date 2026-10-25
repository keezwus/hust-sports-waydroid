#!/bin/bash
# Switch to the visible desktop (for manual repair / login).
systemctl --user stop weston-headless.service
systemctl --user start weston-waydroid.service
systemctl --user is-active weston-waydroid.service
