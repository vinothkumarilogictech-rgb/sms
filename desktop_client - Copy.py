"""Windows desktop shell for the hosted web application.

Build this file into the customer EXE. It opens the configured server URL
inside a native WebView window instead of launching Chrome/Edge with an
address bar.
"""

from __future__ import annotations

import ctypes
import sys

import webview

from desktop_constants import APP_TITLE, get_server_url
from machine_id import get_machine_id


class DesktopBridge:
    def get_device_info(self) -> dict[str, str]:
        return {
            "device_id": get_machine_id(),
            "device_platform": "windows_desktop",
        }


def show_error(message: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(0, message, APP_TITLE, 0)
    except Exception:
        print(message, file=sys.stderr)


def inject_desktop_device_fields(window: webview.Window) -> None:
    script = r"""
    (async function () {
      async function attachDeviceFields() {
        if (!window.pywebview || !window.pywebview.api) return;
        const form = document.getElementById("loginForm") || document.querySelector("form[method='post']");
        if (!form) return;

        const info = await window.pywebview.api.get_device_info();

        function setHidden(name, value) {
          let input = form.querySelector("input[name='" + name + "']");
          if (!input) {
            input = document.createElement("input");
            input.type = "hidden";
            input.name = name;
            form.appendChild(input);
          }
          input.value = value || "";
        }

        setHidden("device_id", info.device_id);
        setHidden("device_platform", info.device_platform);
      }

      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", attachDeviceFields, { once: true });
      } else {
        await attachDeviceFields();
      }
    })();
    """
    try:
        window.evaluate_js(script)
    except Exception as exc:
        print(f"Could not inject desktop device fields: {exc}", file=sys.stderr)


def main() -> None:
    server_url = get_server_url()
    if not server_url.lower().startswith(("http://", "https://")):
        show_error(f"Invalid server URL: {server_url}")
        sys.exit(1)

    bridge = DesktopBridge()
    window = webview.create_window(
        APP_TITLE,
        server_url,
        js_api=bridge,
        width=1280,
        height=800,
        min_size=(1024, 650),
    )
    window.events.loaded += lambda: inject_desktop_device_fields(window)
    webview.start(debug=False)


if __name__ == "__main__":
    main()
