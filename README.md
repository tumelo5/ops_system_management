# Operations Management System

Note: This project is currently in progress. Features and functionality are actively being developed.

## Development Status
Active development is taking place on the `dev` branch.
The `main` branch represents a stable baseline.


## Overview
OPS System Management is a web-based system that tracks POS devices across multiple departments, logging their current status and user activities. It was developed to replace Excel-based tracking, providing a more efficient, accurate, and real-time way to monitor devices and streamline departmental workflows. The project is inspired by real operational processes from my workplace, reflecting practical challenges and solutions in managing POS devices.

## Purpose
The purpose of OPS System Management is to replace the Excel-based tracking system used at my workplace for managing POS devices. Tracking device movement, statuses, and departmental duties manually in Excel was error-prone and hard to audit — for example, finance often found discrepancies between recorded stock usage and actual usage, leading to billing errors and budget miscalculations. At one point, an audit revealed that 95% of parts usage records were incorrect, prompting a process restructure, yet Excel remained in use. This system provides a centralized, real-time platform to monitor POS devices and user responsibilities, improving accuracy, accountability, and operational efficiency.

## Tech Stack
This project leverages a full-stack development approach, including:
Frontend: React.js,CSS, JavaScript
Backend: Django, Python, Node.js
Database: PostgreSQL
Deployment & DevOps: Docker, Kubernetes, GitHub Actions (CI/CD) (planned / in progress)Additional Tools & Libraries: REST APIs, Git & GitHub

This stack demonstrates my ability to handle end-to-end development, from building        interactive user interfaces to backend logic, database management, and production-ready deployment pipelines.

## Features / Key Functionalities
Core Features (In Progress/Planned)
- POS Device Tracking: Monitors the movement of POS devices across multiple departments in real-time.
- Status Logging: Records the current status of each device (e.g., In Use, In Transit, Under Maintenance).
- User Activity Logging: Tracks the duties and actions of users per department, ensuring accountability.
- Centralized Dashboard: Provides a single interface to view device locations, statuses, and user activities.
- Data Accuracy & Auditability: Reduces errors compared to Excel tracking and makes audits easier.
- Real-World Workflow Simulation: Reflects actual operational processes based on workplace experience

## Advanced / Upcoming Features (In Progress/Planned)
- Automated Notifications: Sends alerts when devices change status or need attention.
- Reporting & Analytics: Generates insights on device usage, departmental performance, and audit summaries.
- User Role Management: Different access levels for admins, department users, and auditors.
- Hosted Version Deployment: Accessible online without local setup for easy review.
- CI/CD & Containerization: Full Docker/Kubernetes deployment pipeline planned for production-readiness.

## Project Structure
ops_system_management/
├── backend/              # Server-side application and API
├── core/                 # Django proect settings and configuration
├── frontend/             # Client-side user interface
├── docs/                 # Project documentation
│   ├── ERD.md           # Entity Relationship Diagram
│   ├── ARCHITECTURE.md  # System architecture and design
│   ├── WORKFLOW.md      # Process flows and user journeys
│   └── DECISIONS.md     # Technical decision log
└── README.md             # Project overview and setup guide


## Setup Instructions
You can either run the project locally or access the hosted version (coming soon).

1. Run Locally
Clone the repository
git clone https://github.com/your-username/ops_system_management.git
cd ops_system_management

2. Backend Setup (Django/Python)
Create and activate a virtual environment:
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
# Install dependencies:
pip install -r requirements.txt
# Run database migrations:
python manage.py migrate
# Start the backend server:
python manage.py runserver

2. Frontend Setup (React.js)
cd frontend
npm install
npm start

3. Access the application
Open your browser and go to:
http://localhost:3000


## HR Module Design Decision

The HR module uses predefined choices for departments and positions rather than 
separate database tables with full CRUD operations. This was chosen for the 
demonstration scope of this project.

**Production Consideration:** In a full production environment, departments and 
positions would be implemented as separate models with ForeignKey relationships, 
allowing HR administrators to dynamically add, edit, and remove departments and 
positions through the admin interface without code changes.

**Current Implementation Benefits:**
- Simpler data model for demonstration purposes
- Faster queries (no JOIN operations needed)
- Data integrity through predefined choices
- Sufficient for showcasing the core functionality

