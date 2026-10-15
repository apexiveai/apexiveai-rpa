# MPT POC / DEMO SCOPE

## POC Objective
Demonstrate an end-to-end unattended automation workflow on Windows that starts on a schedule, interacts with a target application, reads/writes data, handles exceptions and produces auditable execution results.

## Demo Workflow A — Web + Excel
1. Scheduler triggers workflow.
2. Robot launches Edge/Chrome.
3. Login to approved test website.
4. Read records.
5. Validate required fields.
6. Write result to Excel.
7. Save output file.
8. Log success/failure.
9. Display run metrics in Control Center.

## Demo Workflow B — Database + API
1. Scheduler starts job.
2. Query test database.
3. Transform records.
4. Call approved REST API.
5. Persist result.
6. Retry transient failure.
7. Produce audit trail.

## Demo Workflow C — Windows Desktop
1. Robot launches approved Windows test application.
2. Identify UI elements.
3. Input data.
4. Capture result.
5. Handle application exception.
6. Continue/stop according to workflow policy.

## Acceptance Criteria
- Scheduled unattended execution
- Successful Windows desktop interaction
- Browser automation
- Excel processing
- Database read/write
- REST call
- Error handling and retry
- Execution log
- Audit record
- Administrator can enable/disable workflow
- Repeatable run with test data

## POC Exclusions
Production credentials, live customer data, destructive database operations and unrestricted command execution are excluded from POC unless separately approved.
