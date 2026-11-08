# Operations Management System (OPS)

> **Status:** in active development. Work happens on the `dev` branch; `main` is a stable baseline. Features are at different stages, see [Implementation Status](#implementation-status).

## Overview

OPS System Management is a web-based application for tracking devices across multiple operational modules, recording their status, their movement and the user activity around them. It gives a device-maintenance provider one place for structured records, defined business rules and controlled workflows.

The domain is modelled on common device-maintenance operations. Business names, figures and policies used in this repository are illustrative.

## Purpose

Tracking devices across several teams needs consistent records, visible movement and clear accountability. OPS addresses this with structured data, enforced business rules and workflows that connect the modules, so records stay accurate and changes can be traced. The design is intended to be adaptable to different business requirements.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | React, JavaScript, CSS |
| Backend | Python, Django, Django REST Framework |
| Notification service | Node.js, Express (Server-Sent Events) |
| Database | PostgreSQL |
| Authentication | JWT (SimpleJWT) with department-based permissions |
| Testing | Django test suite, Playwright (end-to-end), Node.js built-in test runner |
| DevOps | Docker, Docker Compose; GitHub Actions CI/CD and Kubernetes planned |

The project is built incrementally: business requirements first, then data models and backend functionality, then the user interface. Deployment and automation are introduced as the system matures.

## Architecture

The backend follows a strict three-layer pattern:

- **Views** orchestrate HTTP and delegate.
- **Serializers** validate incoming data early.
- **Services** own all business logic and database writes. `transaction.atomic` is used only in this layer.

Models define the constraints that back these rules. Status and department fields use `TextChoices`, and architectural decisions are recorded as ADRs.

A small Node.js service (`notifier/`) is designed to push real-time events to the browser over Server-Sent Events. The backend publishes an event after a transaction commits, and the service delivers it to users of the targeted department, verifying the same JWTs the backend issues.

## Key Features

- **Device tracking:** follows devices and their records through defined operational workflows.
- **Status management:** maintains device statuses as they progress through the system.
- **Structured data and integrity:** relational models, validation and database constraints prevent invalid or inconsistent records.
- **Workflow management:** modules interact through defined business rules.
- **Device rentals:** assigns provider-owned devices to clients in bulk and ends rentals when devices return, with one active rental per device.
- **Department-based access:** users sign in with a JWT that carries their department, and permissions follow it.
- **Traceability:** records device movement, status changes and department activity.

## Implementation Status

| Area | Status |
| --- | --- |
| Authentication and department-based access | Implemented |
| Warehouse: client, model, version and batch management, bulk device scanning, data corrections | Implemented |
| Warehouse: device rentals (bulk assign and end) | Implemented |
| Warehouse: device returning | In design |
| Repairs | Designed (data model and workflows); implementation next |
| Production, Small Parts Stores, Finance | Planned |
| Real-time notifications (Node.js service) | planned |
| Reporting and analytics, hosted deployment, CI/CD | Planned |

## Project Structure

```
ops_system_management/
├── backend/
├── core/
├── frontend/
├── docs/
│   └── BUSINESS_REQUIREMENTS.md
├── docker-compose.yml
├── Dockerfile.backend
├── manage.py
├── requirements.txt
└── README.md
```

## Documentation

The business requirements are in [`docs/BUSINESS_REQUIREMENTS.md`](docs/BUSINESS_REQUIREMENTS.md). Technical documentation, including architecture, database design, workflows and ADRs, will be published progressively as designs are validated against the implementation.

## Setup

OPS is currently intended to run in a local development environment.

1. Configure the environment variables in the `.env` file (see `.env.example`).
2. Start the application with Docker Compose.
3. Open the application at the configured local URL.


