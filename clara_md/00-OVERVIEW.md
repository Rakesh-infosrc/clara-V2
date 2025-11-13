# Clara Virtual Receptionist - Complete POC Documentation

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Key Features](#key-features)
4. [Technology Stack](#technology-stack)
5. [Documentation Structure](#documentation-structure)

---

## Overview

**Clara** is an AI-powered virtual receptionist system designed for enterprise environments. It provides intelligent, multi-lingual conversational interactions for employees, visitors, and candidates through a modern web interface with real-time audio/video capabilities.

### Project Vision

Clara aims to automate and enhance the reception experience by:
- **Automating visitor management** with face recognition and OTP verification
- **Supporting multiple languages** (English, Hindi, Tamil, Telugu)
- **Providing intelligent assistance** for company information and employee queries
- **Streamlining employee verification** through facial recognition and credential checks
- **Managing visitor logs** and host notifications automatically

---

## Architecture

Clara follows a **microservices architecture** deployed on AWS:

```
┌─────────────┐
│   Users     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Application Load Balancer (ALB)   │
└──────┬──────────────────┬───────────┘
       │                  │
       ▼                  ▼
┌─────────────┐    ┌─────────────┐
│  Frontend   │◄───┤   Backend   │
│  (Next.js)  │    │  (FastAPI)  │
└─────────────┘    └──────┬──────┘
                          │
                          ▼
                   ┌─────────────┐
                   │    Agent    │
                   │  (LiveKit)  │
                   └──────┬──────┘
                          │
       ┌──────────────────┼──────────────────┐
       ▼                  ▼                  ▼
┌─────────────┐    ┌─────────────┐   ┌─────────────┐
│  DynamoDB   │    │     S3      │   │  LiveKit    │
│  (Tables)   │    │  (Storage)  │   │   Cloud     │
└─────────────┘    └─────────────┘   └─────────────┘
```

![Clara Flow Diagram](./Clara_flow_diagram_transparent.png)

### Components

1. **Frontend**: Next.js 15 with React 19, TailwindCSS, LiveKit Components
2. **Backend**: FastAPI with Python, handling API requests and flow management
3. **Agent**: LiveKit-based conversational AI with Google STT/TTS
4. **Storage**: DynamoDB for data, S3 for images and documents
5. **External Services**: LiveKit Cloud, Google API, AWS SNS

---

## Key Features

### 🎯 Core Capabilities

- **Multi-lingual Support**: English, Hindi, Tamil, Telugu with real-time language switching
- **Face Recognition**: Employee verification using face encodings stored in S3
- **OTP Verification**: SMS-based authentication via AWS SNS
- **Visitor Management**: Complete visitor lifecycle from registration to host notification
- **Company Information**: AI-powered responses about company services and information
- **Flow-based Conversations**: State machine-driven dialogue management
- **Real-time Communication**: WebRTC-based audio/video using LiveKit

### 🔐 Security Features

- Face recognition with 95%+ accuracy threshold
- OTP-based two-factor authentication
- Secure credential storage in DynamoDB
- IAM-based access control for AWS resources
- Environment-based configuration management

### 🌍 Multi-language Support

- Default conversation language is English until the user explicitly requests a switch
- Explicit language switching supported via one-word or native-script names (English/தமிழ்/తెలుగు/हिंदी)
- Dynamic message translation and language-specific prompts
- Seamless continuation in the selected language for the rest of the flow

---

## Technology Stack

### Frontend
- **Framework**: Next.js 15.5.2 with App Router
- **UI Library**: React 19
- **Styling**: TailwindCSS 4, Radix UI components
- **Real-time**: LiveKit Client SDK, LiveKit Components React
- **State Management**: React hooks and context
- **Build Tool**: Turbopack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Real-time**: LiveKit Server SDK
- **Language Detection**: fasttext (lid.176.ftz model)
- **Face Recognition**: face_recognition library with dlib
- **AWS SDK**: boto3 for DynamoDB, S3, SNS
- **Environment**: python-dotenv for configuration

### Agent
- **Framework**: LiveKit Agents SDK
- **LLM**: Google Gemini 2.0 Flash (Realtime Model)
- **STT**: Google Speech-to-Text
- **TTS**: Google Text-to-Speech
- **Plugins**: noise_cancellation, google plugins

### Infrastructure
- **Compute**: AWS ECS Fargate
- **Load Balancing**: Application Load Balancer (ALB)
- **Database**: Amazon DynamoDB
- **Storage**: Amazon S3
- **Messaging**: AWS SNS
- **Monitoring**: CloudWatch Logs
- **Container Registry**: Amazon ECR
- **IaC**: AWS CloudFormation (SAM)

---

## Documentation Structure

This documentation is organized into the following sections:

1. **[00-OVERVIEW.md](./00-OVERVIEW.md)** - This file, project overview
2. **[01-FRONTEND.md](./01-FRONTEND.md)** - Frontend architecture and components
3. **[02-BACKEND.md](./02-BACKEND.md)** - Backend API and flow management
4. **[03-AGENT.md](./03-AGENT.md)** - LiveKit agent and conversational AI
5. **[04-DEPLOYMENT.md](./04-DEPLOYMENT.md)** - AWS deployment and infrastructure
6. **[05-DATABASE.md](./05-DATABASE.md)** - DynamoDB schema and data models
7. **[06-INTEGRATION.md](./06-INTEGRATION.md)** - External service integrations
8. **[07-DEVELOPMENT.md](./07-DEVELOPMENT.md)** - Local development setup
9. **[08-TROUBLESHOOTING.md](./08-TROUBLESHOOTING.md)** - Common issues and solutions

---

## Quick Start

### Prerequisites
- Node.js 18+ and pnpm
- Python 3.11+
- AWS Account with configured credentials
- LiveKit Cloud account
- Google Cloud API key

### Local Development

```bash
# 1. Clone the repository
git clone <repository-url>
cd clara-V2-add-Languages

# 2. Set up environment variables
cp .env.example .env
# Edit .env with your credentials

# 3. Start backend
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python main.py dev

# 4. Start frontend (new terminal)
cd frontend
pnpm install
pnpm dev

# 5. Access the application
# Frontend: http://localhost:3003
# Backend: http://localhost:8000
```

### Deployment

```bash
# Deploy to AWS ECS Fargate
aws cloudformation deploy \
  --template-file template.yml \
  --stack-name clara-dev \
  --parameter-overrides Stage=dev \
  --capabilities CAPABILITY_IAM
```

---

## Project Statistics

- **Total Lines of Code**: ~15,000+
- **Frontend Components**: 20+
- **Backend Endpoints**: 15+
- **Agent Tools**: 8+
- **Supported Languages**: 4
- **DynamoDB Tables**: 3
- **S3 Buckets**: 3
- **AWS Services Used**: 10+

---

## Contributors

- **Project Lead**: Bijjam Rakesh Reddy
- **Organization**: Info Services
- **Version**: 2.0 (Multi-language Support)

---

## License

Proprietary - Info Services © 2025

---

## Next Steps

- Read **[01-FRONTEND.md](./01-FRONTEND.md)** to understand the UI architecture
- Read **[02-BACKEND.md](./02-BACKEND.md)** to learn about the API layer
- Read **[03-AGENT.md](./03-AGENT.md)** to explore the conversational AI
- Read **[04-DEPLOYMENT.md](./04-DEPLOYMENT.md)** for deployment instructions
