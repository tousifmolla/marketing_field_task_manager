# Database

The normalized SQLAlchemy model contains users/roles, employees and managers, daily attendance, event-based locations, clients and visits, tasks and updates, appointments, photos, automatic activities, monthly payroll, products/orders/items/expenses, notifications and audit logs.

Foreign keys establish ownership. Unique constraints protect usernames, employee/client/task/order codes and one attendance/payroll record per employee period. Frequently filtered dates, owners and statuses are indexed. Store UTC timestamps and display them in the user's timezone.

For PostgreSQL, set `DATABASE_URL`, add Flask-Migrate/Alembic, generate an initial migration from the models and test it against a staging copy.
