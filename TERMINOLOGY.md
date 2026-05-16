# 🛰️ Mission Tracker: System Terminology Reference

This file contains all the terminology used throughout the application. You can modify the **Proposed Tactical** or **Proposed Standard** columns. Once you save this file, let me know, and I will update the system logic accordingly.

| Key | Current Tactical | Current Standard | Meaning / Context | Proposed Tactical | Proposed Standard |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `dashboard` | Command Center | Dashboard | The main landing page after login. | Overview | Dashboard |
| `tasks` | Directives | Tasks | Plural form of task. Used in sidebar and headings. | Actions | Tasks |
| `todo` | AWAITING_EXEC | To Do | Status for tasks that haven't been started. | Queued | To Do |
| `in_progress` | ACTIVE_OP | In Progress | Status for tasks currently being worked on. | Active | In Progress |
| `done` | OBJECTIVE_MET | Completed | Status for finished tasks. | Complete | Completed |
| `users` | Personnel Database | User Management | Page for managing team members. | Team | User Management |
| `audit_log` | System Records | Audit Log | Page showing the history of all changes. | Activity Log | Audit Log |
| `search` | Database Query | Search Engine | The global search interface. | Search | Search |
| `analytics` | Telemetry Data | Analytics | The progress reporting / stats page. | Insights | Analytics |
| `mission` | Mission Operation | Mission | The top-level hierarchy (e.g., "Field Research"). | Campaign | Mission |
| `project` | Node Cluster | Project | The second-level hierarchy (e.g., "Club Calibration"). | Stream | Project |
| `task` | Directive Unit | Task | The third-level hierarchy (individual items). | Item | Task |
| `overdue` | STALE_TASK | Overdue | Tasks past their deadline. | Past Due | Overdue |
| `due_today` | URGENT_SYNC | Due Today | Tasks with a deadline of today. | Due Today | Due Today |
| `due_this_week` | UPCOMING_OPS | Due This Week | Tasks due within 7 days. | This Week | Due This Week |
| `upcoming` | PLANNED_TRAJECTORY | Upcoming | Tasks due in the future. | Scheduled | Upcoming |
| `no_due` | ASYNC_UNSET | No Due Date | Tasks without a set deadline. | Flexible | No Due Date |
| `priority` | THREAT_LEVEL | Priority | The importance level (Low, Medium, High). | Priority | Priority |
| `status` | OPERATIONAL_STATUS | Status | The current state of a task or mission. | Status | Status |
| `lead` | Commanding_Officer | Project Lead | The user in charge of a project. | Lead | Project Lead |
| `member` | Member_Operative | Member | A standard user/member. | Member | Member |
| `admin` | System_Admin | Administrator | A user with full system control. | Admin | Administrator |

## 🛠️ How to Update
1.  Fill in the **Proposed Tactical** or **Proposed Standard** columns with your desired words.
2.  If you leave a field blank, the current value will be kept.
3.  Save the file.
4.  **Tell me: "I've updated TERMINOLOGY.md, please apply the changes."**
