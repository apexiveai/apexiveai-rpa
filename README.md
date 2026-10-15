# Apexive AI — MPT Enterprise RPA Platform

A local-first RPA Studio prototype with a visual workflow designer, FastAPI orchestrator, persistent execution queue, and a separate Windows desktop robot.

## Components
- **Studio:** Next.js visual workflow editor for projects, ordered browser and desktop automation steps, saving and manual execution.
- **Orchestrator:** FastAPI + SQLAlchemy API; stores workflows and run history, queues runs, assigns them to authenticated robots, tracks worker heartbeats, and records completion/audit events.
- **Windows Robot:** Long-polling worker using Playwright for Chrome/Edge web automation and pywinauto UI Automation for Windows desktop applications.
- **Database:** SQLAlchemy database configured with `DATABASE_URL` (PostgreSQL for deployment; SQLite can be used for local development).

The scheduler, Excel/Outlook/database connectors, credential vault, and production RBAC are not implemented yet. Chrome/Edge automation is available alongside Windows UI automation.

## Run locally on Windows

1. Configure the backend:

   ```cmd
   cd backend
   py -3.12 -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   copy .env.example .env
   ```

   Set `DATABASE_URL` to a reachable database and replace `SECRET_KEY` and `ROBOT_TOKEN` in `.env` with unique, high-entropy values. The robot token is a separate shared secret used only by trusted workers. For local SQLite, use `DATABASE_URL=sqlite:///./apexive_rpa.db`; SQLite is intended for development, not multi-robot production use.

2. Start the API in the activated backend environment:

   ```cmd
   uvicorn app.main:app --reload --port 8111
   ```

3. Start the Studio in another terminal:

   ```cmd
   cd frontend
   npm install
   npm run dev
   ```

   Open `http://localhost:3030`. Set `NEXT_PUBLIC_API_URL` if the API is not at `http://localhost:8111/api`. Include the Studio origin in backend `CORS_ORIGINS`.

4. Start a Windows Robot in an interactive Windows 10/11 user session, with the backend virtual environment activated:

   ```cmd
   cd backend
   .\.venv\Scripts\activate
   set RPA_ROBOT_TOKEN=the_same_value_as_ROBOT_TOKEN
   python -m robot.worker --api-url http://127.0.0.1:8111/api
   ```

   The worker must run in the desktop session that is allowed to interact with the target application; do not run UI automation in Windows Session 0 as a service. Use a dedicated, least-privilege Windows account. The worker polls for queued runs and reports step output and failures to the orchestrator.

   Install Chrome and/or Edge in that Windows user environment. Browser steps launch an isolated, temporary Playwright context using the selected installed browser; cookies and sessions are not preserved across runs. Headless mode is available for unattended browser workflows.

## Visual designer actions

- Browser launch (`browser_launch`): choose installed Google Chrome or Microsoft Edge and visible/headless mode.
- Browser navigation (`browser_navigate`): navigate to HTTP(S) URLs only (no embedded credentials or script/file URLs).
- Browser click/fill/press/select (`browser_click`, `browser_fill`, `browser_press`, `browser_select`): use CSS/Playwright selectors and interpolated workflow variables.
- Browser wait (`browser_wait`): wait for an element to attach, detach, become visible, or become hidden.
- Browser text (`browser_get_text`, `browser_assert_text`): read up to 10,000 characters into run output/optional variable, or assert exact/contained text.
- Browser close (`browser_close`): close the current browser context.
- Launch Windows application (`launch_app`): executable path and optional argument list; started without a shell.
- Wait for window (`wait_for_window`): title and timeout.
- Click UI element (`click`): UI Automation title, automation ID, and/or control type.
- Type text (`type_text`): text into a selected edit control or the active window.
- Press key (`press_key`): pywinauto key notation, e.g. `{ENTER}` or `{TAB}`.
- Close window (`close_window`).
- Set variable (`set_variable`), delay (`delay`, maximum 3600 seconds), and log (`log`).

Text and URL fields accept `${variable_name}` interpolation for variables previously set in the same run. Browser sessions use fresh contexts, do not accept downloads, and are closed at workflow completion or failure. The worker only executes its explicit action allowlist; it does not provide a shell, Python script, or arbitrary command action. The browser can access network resources reachable by the robot, so restrict workflow authors and the robot account to approved sites and networks.

## Development notes

- API docs: `http://localhost:8111/docs`
- Runs remain `queued` until a robot claims them; they are not reported as successful before execution.
- Robot routes use `X-Robot-Token`. If `ROBOT_TOKEN` is unset, claim and completion endpoints return `503`.
- The worker reports unsupported/malformed actions as failed runs rather than executing them.
- `backend/tests` contains backend tests; run from `backend` with `python -m pytest`.
