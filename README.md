# Operations Management System

Note: This project is currently in progress. Features and functionality are actively being developed.

## Development Status
Active development is taking place on the `dev` branch.
The `main` branch represents a stable baseline.


## Overview
OPS System Management is a web-based application designed to track devices across multiple operational modules, recording their status, movement, and relevant user activities. The system aims to provide a centralized alternative to spreadsheet-based tracking, improving visibility, data consistency, accountability, and workflow management.

The project is informed by practical operational challenges and explores how software can support structured processes, reliable record-keeping, and better data management.

## Purpose
The purpose of OPS System Management is to improve how devices, their statuses, and related activities are tracked and managed. Spreadsheet-based approaches can make it difficult to maintain consistent records, monitor device movement, and establish clear accountability across workflows.

OPS aims to address these challenges through a centralized system with structured data, defined business rules, and controlled workflows. The goal is to improve record accuracy, traceability, and operational efficiency while providing a foundation that can be adapted to different business requirements.

## Tech Stack
OPS System Management uses a full-stack architecture:
Frontend: React.js, CSS, JavaScript
Backend: Django, Python, Django REST Framework
Database: PostgreSQL
Deployment & DevOps: Docker, Kubernetes, GitHub Actions (CI/CD) (planned)

The project is being developed incrementally, from defining business requirements and designing data models to implementing backend functionality and building the user interface. Deployment and automation will be introduced as the system matures.

## Features / Key Functionalities
Core Features
- Device Tracking: Tracks devices and their associated records throughout defined operational workflows.
- Status Management: Maintains device statuses as they progress through the system.
- Structured Data Management: Uses relational data models and validation to maintain data consistency.
- Workflow Management: Supports interactions between operational modules through defined business rules.
- Data Integrity: Applies validation and database constraints to help prevent invalid or inconsistent records.
- Activity Traceability: Provides a foundation for recording relevant user actions and changes.

Implementation status varies by feature as development continues.

## Planned / Upcoming Features
- Automated Notifications: Alerts users when defined events or conditions require attention.
- Reporting & Analytics: Summarizes operational data to support monitoring and decision-making.
- Role-Based Access Control: Restricts functionality and data access according to user roles and permissions.
- Hosted Deployment: Makes the application accessible online for demonstration and review.
- Containerization & CI/CD: Introduces Docker-based deployment and automated workflows using GitHub Actions, with Kubernetes considered      for orchestration where appropriate.


## Project Structure
ops_system_management/
├── backend/
├── core/
├── frontend/
├── docs/
│   └── ops_system_management/
│       ├── BUSINESS_REQUIREMENTS.md
│       ├── ARCHITECTURE.md
│       ├── ERD.md
│       ├── WORKFLOW.md
│       └── DECISIONS.md
├── docker-compose.yml
├── Dockerfile.backend
├── manage.py
├── requirements.txt
└── README.md         

## Documentation

Business requirements are being documented to establish the system's intended functionality and expected behavior.

Technical documentation, including architecture, database design, and workflow details, will be progressively published as the implementation develops and the corresponding designs are validated.

## Setup Instructions
OPS System Management is currently intended to run in a local development environment.

1. Configure the environment variables in the .env file.
2. Start the application using Docker Compose.
3. Access the application through the configured local URL.


