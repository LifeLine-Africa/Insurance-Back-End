![LifeLine Africa Logo](https://i.imgur.com/i6Lfiku.png)
# LifeLine Africa Insurance API

A robust insurance application API built with Flask that handles submissions, generates PDF documents, and sends email notifications.

## Table of Contents
1. [Features](#features)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Development Setup](#development-setup)
5. [Production Deployment](#production-deployment)
   - [Docker Deployment](#docker-deployment-recommended)
   - [Manual Deployment](#manual-deployment)
6. [Configuration](#configuration)
7. [API Endpoints](#api-endpoints)
8. [Database Management](#database-management)
9. [Maintenance](#maintenance)
10. [Troubleshooting](#troubleshooting)
11. [Security](#security)
12. [License](#license)

## Features
- **Multi-type Submissions**: Handle both individual and company insurance applications
- **Automated PDF Generation**: Professionally formatted PDF documents with branding
- **Email Notifications**: Send to multiple recipients with CC capabilities
- **Database Integration**: Supports SQLite (development) and MongoDB (production)
- **Health Monitoring**: Built-in health check endpoint
- **Comprehensive Logging**: Detailed request and error logging

## Prerequisites

### For Development
- Python 3.11+
- SQLite
- SMTP credentials for email testing

### For Production
| Component | Requirement |
|-----------|-------------|
| OS | Ubuntu 20.04+/CentOS 8+ |
| Memory | 2GB RAM (4GB recommended) |
| Storage | 20GB+ available |
| Python | 3.11+ |
| Services | MongoDB 4.4+, Redis 6.0+ |
| Network | Outbound HTTPS/SMTP access |

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/insurance-back-end
   cd insurance-back-end
   ```

2. Set up environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate    # Windows
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python app.py
   ```

# Development Setup
## Initial Configuration
1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit .env with your settings:
   ```bash
   DEBUG=True
   SECRET_KEY=your-dev-secret-key
   SQLALCHEMY_DATABASE_URI=sqlite:///instance/insurance.db
   ```

3. Initialize the database:
   ```bash
   flask init-db
   ```

## Running Tests
```bash
python -m pytest tests/
```

## Configuration
### Environment Variables
   | Variable            | Required | Description                   | Example                          |
|---------------------|----------|-------------------------------|----------------------------------|
| `DEBUG`             | Yes      | Debug mode                    | `False` in production            |
| `SECRET_KEY`        | Yes      | Flask secret key              | Random string                    |
| `DATABASE_URI`      | Yes      | Database connection string    | `mongodb://user:pass@host:port/db` |
| `SMTP_SERVER`       | Yes      | SMTP host                     | `smtp.gmail.com`                 |
| `SMTP_PORT`         | Yes      | SMTP port                     | `465`                            |
| `PRIMARY_RECIPIENTS`| Yes      | Main recipients               | `["admin@domain.com"]`           |

## Email Configuration
```bash
SMTP_USERNAME=your@email.com
SMTP_PASSWORD=your-password
EMAIL_FROM_NAME=LifeLine Africa
EMAIL_FROM_ADDRESS=noreply@domain.com
```

## API Endpoints

| Endpoint                 | Method | Description                     |
|--------------------------|--------|---------------------------------|
| `/submit`               | POST   | Submit new insurance application |
| `/download-pdf/<id>`    | GET    | Download generated PDF           |
| `/submission/<id>`      | GET    | View submission details          |
| `/health`               | GET    | System health check              |

# License
This project is licensed under The Lifeline Africa License
