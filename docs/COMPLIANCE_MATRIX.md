# MPT RPA REQUIREMENT — COMPLIANCE MATRIX

Legend: **C = Compliant/Planned**, **P = POC validation**, **E = Enhancement subject to final scope**

| # | Requirement | Apexive AI Response | Status |
|---|---|---|---|
| 1 | Windows 10+ | Windows Worker | C/P |
| 2 | RPA Project New/Modify/Publish/Delete | Project lifecycle API + Studio | C/P |
| 3 | Executor/Scheduler 24/7 by interval | Scheduler + unattended worker | C/P |
| 4 | Workflow Create/Modify/Disable/Enable/Delete | Workflow registry/API | C/P |
| 5 | Loop/Continue/Break/Exit/Delay/Block/TryCatch | Workflow engine nodes | P |
| 6 | Windows applications | Windows automation worker | P |
| 7 | Chrome/Firefox/Edge | Playwright worker | P |
| 8 | Outlook/Excel/Word | Office automation adapters | P |
| 9 | Image recognition/data scraping | UI recognition + extraction adapters | P |
| 10 | Global/Local variables | Workflow context | C/P |
| 11 | Oracle/MySQL/MSSQL | DB connector layer | P |
| 12 | Query/Insert/Update/Delete | DB action layer | P |
| 13 | System commands | Allowlisted worker actions | P |
| 14 | File/folder management | File action layer | C/P |
| 15 | REST/SOAP | Integration adapters | P |
| 16 | Python | Worker script adapter | P |
| 17 | Math/Datetime/Clipboard/Text/ZIP/etc. | Utility action library | C/P |
| 18 | Message Box / Log / Error | Execution telemetry | C/P |
| 19 | Debugging and Logs | Run history + structured logs | C/P |
| 20 | Developer Guide | Documentation deliverable | C |
| 21 | Scalability/Stability | Queue + stateless API + workers | P |
| 22 | Security Features | RBAC, TLS, secrets, audit | P |
| 23 | Technical Support | Enterprise support package | C |
| 24 | Trial License | Time-limited POC license | C |
| 25 | Additional Features | AI, integrations, custom connectors | E |

Final status should be updated after POC validation; no item should be represented as production-certified until tested in MPT's environment.
