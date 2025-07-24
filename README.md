# LifeLine Africa Insurance API - Production Deployment Guide

## Overview

This guide covers the complete production deployment of the LifeLine Africa Insurance API, a high-performance Flask application with enterprise-grade features.

## Prerequisites

### System Requirements
- **Operating System**: Ubuntu 20.04+ or CentOS 8+
- **Python**: 3.11+
- **Memory**: Minimum 2GB RAM (4GB+ recommended)
- **Storage**: 20GB+ available space
- **Network**: Outbound HTTPS/SMTP access for email delivery

### Required Services
- **MongoDB**: 4.4+ (local or MongoDB Atlas)
- **Redis**: 6.0+ (for rate limiting and caching)
- **SMTP Server**: Gmail or corporate email server
- **SSL Certificate**: Let's Encrypt or commercial certificate

##  Installation Methods

### Method 1: Docker Deployment (Recommended)

#### 1. Clone and Setup
```bash
git clone <repository-url>
cd Insurance-Back-End
cp .env.example .env
```

#### 2. Configure Environment Variables
Edit `.env file with your production values:
```bash
# Production Configuration
DEBUG=false
SECRET_KEY=your-production-secret-key-here
FORCE_HTTPS=true

# Database
MONGO_URI=mongodb://mongo:27017/yourmongodb
# Or for MongoDB Atlas:
# MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/yourmongodb

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM_NAME=LifeLine Africa Insurance
EMAIL_FROM_ADDRESS=noreply@yourdomain.com

# Recipients
PRIMARY_RECIPIENTS=["admin@yourdomain.com","insurance@yourdomain.com"]
CC_RECIPIENTS=["notifications@yourdomain.com"]

# Additional Security
ALLOWED_ORIGINS=https://yourdomain.com,https://api.yourdomain.com
```

#### 3. Set Additional Environment Variables
Create `.env.docker` for Docker-specific settings:
```bash
# Database Passwords
MONGO_ROOT_PASSWORD=secure-mongo-password
REDIS_PASSWORD=secure-redis-password

# Application
PORT=5000
GUNICORN_WORKERS=4
```

#### 4. Deploy with Docker Compose
```bash
# Start core services
docker-compose up -d insurance-api mongo redis

# Start with monitoring (optional)
docker-compose --profile monitoring up -d

# Start with logging (optional)
docker-compose --profile logging up -d

# Start everything
docker-compose --profile monitoring --profile logging up -d
```

####
