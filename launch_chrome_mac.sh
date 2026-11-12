#!/usr/bin/env bash
# ========================================================
# Launch Real Google Chrome with Local Profile on macOS
# Port: 9222 (for Automation Bot to connect)
# Target: https://www.avanture.net/
# ========================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
PROFILE_DIR="$DIR/chrome_profile"

mkdir -p "$PROFILE_DIR"

if [ -f "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]; then
    CHROME_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
elif [ -f "$HOME/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]; then
    CHROME_BIN="$HOME/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
elif [ -f "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser" ]; then
    CHROME_BIN="/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
else
    CHROME_BIN="google-chrome"
fi

echo "Launching: $CHROME_BIN"
"$CHROME_BIN" --remote-debugging-port=9222 --user-data-dir="$PROFILE_DIR" "https://www.avanture.net/" &

