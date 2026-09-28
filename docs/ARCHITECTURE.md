# Architecture

Flutter communicates with versioned Flask REST endpoints over HTTP during local development and HTTPS in production. JWT identifies the user; APIs derive the employee from that identity instead of trusting mobile-supplied employee IDs. Flask Blueprints separate domains, SQLAlchemy provides database portability, and services centralize automatic activity/audit creation and payroll calculation.

The Jinja2/Bootstrap dashboard is a separate manager-facing web surface. SQLite and local uploads keep the demo free. PostgreSQL, object storage, Redis-backed JWT revocation and FCM can replace these adapters later without changing the domain model.

Location is captured only during explicit, work-related operations. There is no background or secret tracking.
