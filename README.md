![CI](https://github.com/tumelo5/ops_system_management/actions/workflows/ci.yml/badge.svg?branch=dev)

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
| API documentation | OpenAPI / Swagger UI (drf-spectacular) |
| Database | PostgreSQL |
| Authentication | JWT (SimpleJWT) with department-based permissions |
| Testing | Django test suite (about 200 tests) |
| DevOps | Docker, Docker Compose, GitHub Actions CI; Kubernetes planned |
| Planned | Notification service (Node.js, Express, Server-Sent Events), Playwright end-to-end tests |

The project is built incrementally: business requirements first, then data models and backend functionality, then the user interface. Deployment and automation are introduced as the system matures.

## Architecture

The backend follows a strict three-layer pattern:

- **Views** orchestrate HTTP and delegate.
- **Serializers** validate incoming data early and enforce the real limits server-side.
- **Services** own all business logic and database writes. `transaction.atomic` is used only in this layer.

Models define the constraints that back these rules. Status and department fields use `TextChoices`, and architectural decisions are recorded as ADRs.

A small Node.js service is planned to push real-time events to the browser over Server-Sent Events. The backend would publish an event after a transaction commits, and the service would deliver it to users of the targeted department, verifying the same JWTs the backend issues.

## Key Features

- **Device tracking:** follows devices and their records through defined operational workflows.
- **Status management:** maintains device statuses as they progress through the system.
- **Structured data and integrity:** relational models, validation and database constraints prevent invalid or inconsistent records.
- **Workflow management:** modules interact through defined business rules.
- **Device rentals:** assigns provider-owned devices to clients in bulk, each with a required expected return date, and ends one or many rentals through a single endpoint. Batches are all-or-nothing, and the database allows only one active rental per device.
- **Department-based access:** users sign in with a JWT that carries their department, and permissions follow it.
- **Traceability:** records device movement, status changes and department activity.
- **Documented API:** every endpoint is described in interactive Swagger UI.

## Engineering Highlights

- **Concurrency safety:** rentals lock device and rental rows in a stable order inside one transaction, so two agents cannot rent or end the same device at once.
- **All-or-nothing batches:** a bad item rolls the whole batch back, and the error names the device that blocked it.
- **Rules live in one layer:** services hold the business rules, so the views stay thin and the rules are tested directly.
- **Automated tests in CI:** the Django suite runs on every push against a clean PostgreSQL on Python 3.12.

## Implementation Status

| Area | Status |
| --- | --- |
| Authentication and department-based access | Implemented |
| Warehouse: client, model, version and batch management, bulk device scanning, data corrections | Implemented |
| Warehouse: device rentals (bulk assign and end) | Implemented |
| Warehouse: device returning | In design |
| API documentation (Swagger), Docker setup, CI (GitHub Actions) | Implemented |
| Repairs | Designed (data model and workflows); implementation next |
| Production, Small Parts Stores, Finance | Planned |
| Real-time notifications (Node.js service) | Planned |
| Reporting and analytics, hosted deployment | Planned |

## Project Structure

```
ops_system_management/
├── .github/workflows/ci.yml
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

- **API reference:** interactive Swagger UI at `http://localhost:8000/swagger/` once the app is running. <!-- verify the route -->
- **Business requirements:** [`docs/BUSINESS_REQUIREMENTS.md`](docs/BUSINESS_REQUIREMENTS.md).
- **Technical documentation:** architecture, database design, workflows and ADRs will be published progressively as designs are validated against the implementation.

## Setup

OPS is intended to run in a local development environment. You need [Docker](https://www.docker.com/) with Docker Compose.

```bash
git clone https://github.com/tumelo5/ops_system_management.git
cd ops_system_management
cp .env.example .env        # optional: the defaults already work for local use
docker compose up --build
```

Then open:

- **App:** http://localhost:3000
- **API:** http://localhost:8000
- **Swagger UI:** http://localhost:8000/swagger/ <!-- verify the route -->

The migrations run automatically on start. The credentials in the compose file are for local development only, so don't reuse them anywhere else. <!-- add the demo login here if the Demo Access panel is part of the public build -->

To stop everything: `docker compose down` (add `-v` to also delete the local database).

## Running the Tests

```bash
docker compose run --rm backend python manage.py test
```

Or without Docker, with Python 3.12 and a local PostgreSQL configured in `.env`:

```bash
pip install -r requirements.txt
python manage.py test
```

The same suite runs automatically on every push through GitHub Actions.