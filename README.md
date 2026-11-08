# Operations Management System

Note: This project is currently in progress. Features and functionality are actively being developed.

## Development Status
Active development is taking place on the `dev` branch.
The `main` branch represents a stable baseline.


## Overview
OPS System Management is a web-based application for tracking devices across multiple operational modules, recording their status, their movement and the user activity around them. It gives a device-maintenance provider one place for structured records, defined business rules and controlled workflows.

The domain is modelled on common device-maintenance operations. Business names, figures and policies used in this repository are illustrative.

## Purpose
Tracking devices across several teams needs consistent records, visible movement and clear accountability. OPS addresses this with structured data, enforced business rules and workflows that connect the modules, so records stay accurate and changes can be traced. The design is intended to be adaptable to different business requirements.

OPS aims to address these challenges through a centralized system with structured data, defined business rules, and controlled workflows. The goal is to improve record accuracy, traceability, and operational efficiency while providing a foundation that can be adapted to different business requirements.

## Tech Stack
Layer	Technology
Frontend	React, JavaScript, CSS
Backend	Python, Django, Django REST Framework
Notification service	Node.js, Express (Server-Sent Events)
Database	PostgreSQL
Authentication	JWT (SimpleJWT) with department-based permissions
Testing	Django test suite, Playwright (end-to-end), Node.js built-in test runner
DevOps	Docker, Docker Compose; GitHub Actions CI/CD and Kubernetes planned

The project is being developed incrementally, from defining business requirements and designing data models to implementing backend functionality and building the user interface. Deployment and automation will be introduced as the system matures.

## Architecture

The backend follows a strict three-layer pattern:

Views orchestrate HTTP and delegate.
Serializers validate incoming data early.
Services own all business logic and database writes. transaction.atomic is used only in this layer.

## Features / Key Functionalities
Core Features
- Device tracking: follows devices and their records through defined operational workflows.
- Status management: maintains device statuses as they progress through the system.
- Structured data and integrity: relational models, validation and database constraints prevent invalid or inconsistent records.
- Workflow management: modules interact through defined business rules.
- Device rentals: assigns provider-owned devices to clients in bulk and ends rentals when devices return, with one active rental per device.
- Department-based access: users sign in with a JWT that carries their department, and permissions follow it.
- Traceability: records device movement, status changes and department activity.

Implementation Status
Area	Status
Authentication and department-based access	Implemented
Warehouse: client, model, version and batch management, bulk device scanning, data corrections	Implemented
Warehouse: device rentals (bulk assign and end)	Implemented
Warehouse: device returning	In design
Repairs	Designed (data model and workflows); implementation next
Production, Small Parts Stores, Finance	Planned
Real-time notifications (Node.js service)	Service implemented; backend integration in progress
Reporting and analytics, hosted deployment, CI/CD	Planned

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
│       ├── BUSINESS_REQUIREMENTS.md
├── docker-compose.yml
├── Dockerfile.backend
├── manage.py
├── requirements.txt
└── README.md         

## Documentation

The business requirements are in docs/BUSINESS_REQUIREMENTS.md. Technical documentation, including architecture, database design, workflows and ADRs, will be published progressively as designs are validated against the implementation.

## Setup Instructions
OPS System Management is currently intended to run in a local development environment.

1. Configure the environment variables in the .env file.
2. Start the application using Docker Compose.
3. Access the application through the configured local URL.


