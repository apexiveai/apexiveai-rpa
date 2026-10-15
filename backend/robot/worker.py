import argparse
import os
import re
import subprocess
import sys
import threading
import time
from typing import Any

import httpx

from .browser import BrowserSession


class RobotExecution:
    def __init__(self) -> None:
        self.variables: dict[str, Any] = {}
        self.application: Any = None
        self.process: subprocess.Popen[bytes] | None = None
        self.steps: list[dict[str, Any]] = []
        self.browser = BrowserSession()

    def render(self, value: Any) -> Any:
        if not isinstance(value, str):
            return value

        def replace(match: re.Match[str]) -> str:
            name = match.group(1)
            if name not in self.variables:
                raise ValueError(f"Workflow variable is not defined: {name}")
            return str(self.variables[name])

        return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", replace, value)

    def window(self, step: dict[str, Any]):
        if self.application is None:
            raise RuntimeError("Launch an application before interacting with a window")
        selectors = {
            key: self.render(step[key])
            for key in ("title", "auto_id", "control_type")
            if step.get(key) not in (None, "")
        }
        if not selectors:
            raise ValueError("Desktop action requires at least one of title, auto_id or control_type")
        return self.application.top_window().child_window(**selectors)

    def execute_step(self, step: dict[str, Any]) -> dict[str, Any]:
        action = step.get("action")
        if not isinstance(action, str):
            raise ValueError("Workflow action must be a string")
        if action == "log":
            message = str(self.render(step.get("message", "")))
            print(message, flush=True)
            result: Any = {"message": message}
        elif action == "set_variable":
            name = str(step.get("name", "")).strip()
            if not name:
                raise ValueError("set_variable requires a variable name")
            value = self.render(step.get("value"))
            self.variables[name] = value
            result = {"name": name, "value": value}
        elif action == "delay":
            seconds = float(step.get("seconds", 0))
            if seconds < 0 or seconds > 3600:
                raise ValueError("delay seconds must be between 0 and 3600")
            time.sleep(seconds)
            result = {"seconds": seconds}
        elif action == "launch_app":
            from pywinauto import Application

            executable = str(self.render(step.get("executable", ""))).strip()
            arguments = step.get("arguments", [])
            if not executable or not isinstance(arguments, list) or not all(
                isinstance(arg, str) for arg in arguments
            ):
                raise ValueError("launch_app requires an executable and a list of string arguments")
            self.process = subprocess.Popen(
                [executable, *(str(self.render(arg)) for arg in arguments)],
                shell=False,
            )
            self.application = Application(backend="uia").connect(process=self.process.pid, timeout=30)
            result = {"process_id": self.process.pid}
        elif action == "wait_for_window":
            from pywinauto import Application

            title = str(self.render(step.get("title", ""))).strip()
            if not title:
                raise ValueError("wait_for_window requires a window title")
            timeout = float(step.get("timeout", 30))
            if timeout <= 0 or timeout > 300:
                raise ValueError("window timeout must be between 0 and 300 seconds")
            self.application = Application(backend="uia").connect(title=title, timeout=timeout)
            result = {"title": title}
        elif action == "click":
            self.window(step).click_input()
            result = {"clicked": True}
        elif action == "type_text":
            text = str(self.render(step.get("text", "")))
            control = self.window(step) if any(step.get(key) for key in ("title", "auto_id", "control_type")) else None
            if control is not None:
                control.set_edit_text(text)
            elif self.application is not None:
                self.application.top_window().type_keys(text, with_spaces=True)
            else:
                raise RuntimeError("Launch or attach to an application before typing")
            result = {"characters": len(text)}
        elif action == "press_key":
            key = str(step.get("key", "")).strip()
            if not key or self.application is None:
                raise ValueError("press_key requires a key and an active application")
            self.application.top_window().type_keys(key)
            result = {"key": key}
        elif action == "close_window":
            if self.application is None:
                raise RuntimeError("Launch or attach to an application before closing a window")
            self.application.top_window().close()
            result = {"closed": True}
        elif action.startswith("browser_"):
            result = self.browser.execute(step, self.render)
            if action == "browser_get_text" and result.get("variable"):
                self.variables[result["variable"]] = result["text"]
        else:
            raise ValueError(f"Unsupported Windows Robot action: {action}")

        output = {"step": len(self.steps) + 1, "action": action, "status": "success", "output": result}
        self.steps.append(output)
        return output

    def execute(self, definition: dict[str, Any]) -> dict[str, Any]:
        steps = definition.get("steps", [])
        if not isinstance(steps, list):
            raise ValueError("Workflow definition steps must be a list")
        try:
            for step in steps:
                if not isinstance(step, dict):
                    raise ValueError("Every workflow step must be an object")
                self.execute_step(step)
        finally:
            self.browser.close()
        return {"variables": self.variables, "steps": self.steps}


def run_worker(api_url: str, token: str, worker_name: str, poll_seconds: float) -> None:
    headers = {"X-Robot-Token": token}
    heartbeat_stop = threading.Event()

    def keep_alive() -> None:
        with httpx.Client(base_url=api_url.rstrip("/"), headers=headers, timeout=10) as heartbeat_client:
            while not heartbeat_stop.wait(10):
                try:
                    response = heartbeat_client.post(
                        "/rpa/robot/heartbeat",
                        json={"worker_name": worker_name},
                    )
                    response.raise_for_status()
                except httpx.HTTPError as exc:
                    print(f"Robot heartbeat failed: {exc}", file=sys.stderr, flush=True)

    threading.Thread(target=keep_alive, name="robot-heartbeat", daemon=True).start()
    with httpx.Client(base_url=api_url.rstrip("/"), headers=headers, timeout=35) as client:
        print(f"Windows Robot '{worker_name}' polling {api_url}", flush=True)
        while True:
            try:
                response = client.post(
                    "/rpa/robot/claim",
                    json={"worker_name": worker_name},
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise RuntimeError(
                    f"Robot claim failed ({exc.response.status_code}): {exc.response.text}"
                ) from exc
            except httpx.RequestError as exc:
                print(f"Orchestrator connection failed: {exc}", file=sys.stderr, flush=True)
                time.sleep(poll_seconds)
                continue

            job = response.json()
            if job is None:
                time.sleep(poll_seconds)
                continue

            execution = RobotExecution()
            try:
                output = execution.execute(job["definition"])
                completion = {"status": "success", "output": output}
            except Exception as exc:
                completion = {
                    "status": "failed",
                    "error": str(exc),
                    "output": {"variables": execution.variables, "steps": execution.steps},
                }
                print(
                    f"Run #{job['run_id']} failed: {exc}",
                    file=sys.stderr,
                    flush=True,
                )

            result = client.post(
                f"/rpa/robot/runs/{job['run_id']}/complete",
                json=completion,
            )
            result.raise_for_status()
            print(
                f"Run #{job['run_id']} finished: {completion['status']}",
                flush=True,
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Apexive Windows RPA Robot")
    parser.add_argument("--api-url", default="http://127.0.0.1:8111/api")
    parser.add_argument("--token", default=os.getenv("RPA_ROBOT_TOKEN"))
    parser.add_argument("--name", default=os.getenv("COMPUTERNAME", "windows-robot"))
    parser.add_argument("--poll-seconds", type=float, default=2)
    args = parser.parse_args()

    if os.name != "nt":
        parser.error("The desktop worker must run on Windows 10/11")
    if not args.token:
        parser.error("Set --token or RPA_ROBOT_TOKEN to the configured ROBOT_TOKEN")
    if args.poll_seconds < 0.5:
        parser.error("--poll-seconds must be at least 0.5")
    run_worker(args.api_url, args.token, args.name, args.poll_seconds)


if __name__ == "__main__":
    main()
