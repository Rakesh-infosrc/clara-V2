# Clara Virtual Receptionist - Complete Documentation

## 📚 Documentation Index

Welcome to the complete documentation for the Clara Virtual Receptionist POC. This documentation covers all aspects of the system from architecture to deployment.

---

## 📖 Documentation Files

### Core Documentation

1. **[00-OVERVIEW.md](./00-OVERVIEW.md)** ⭐ **START HERE**
   - Project overview and vision
   - High-level architecture
   - Key features and capabilities
   - Technology stack
   - Quick start guide

2. **[01-FRONTEND.md](./01-FRONTEND.md)**
   - Next.js 15 architecture
   - React 19 components
   - LiveKit integration
   - UI/UX implementation
   - Custom hooks and utilities
   - Styling with TailwindCSS

3. **[02-BACKEND.md](./02-BACKEND.md)**
   - FastAPI application structure
   - Flow management system
   - Agent state management
   - Multi-language message system
   - API endpoints documentation
   - Tool implementations

4. **[03-AGENT.md](./03-AGENT.md)**
   - LiveKit agent architecture
   - Google Gemini 2.0 integration
   - Speech-to-text and text-to-speech
   - Function tools and capabilities
   - Wake word detection
   - Language detection with FastText

5. **[04-DEPLOYMENT.md](./04-DEPLOYMENT.md)**
   - ECS Fargate deployment guide
   - Serverless deployment option
   - Docker containerization
   - CloudFormation templates
   - CI/CD pipeline setup
   - Monitoring and logging

6. **[05-DATABASE.md](./05-DATABASE.md)**
   - DynamoDB table schemas
   - S3 bucket structure
   - Data access patterns
   - Security and encryption
   - Backup and recovery
   - Performance optimization

---

## 🎯 Quick Navigation

### For Developers

- **Getting Started**: [00-OVERVIEW.md](./00-OVERVIEW.md#quick-start)
- **Frontend Development**: [01-FRONTEND.md](./01-FRONTEND.md)
- **Backend API**: [02-BACKEND.md](./02-BACKEND.md#api-endpoints)
- **Agent Development**: [03-AGENT.md](./03-AGENT.md)

### For DevOps

- **Deployment Guide**: [04-DEPLOYMENT.md](./04-DEPLOYMENT.md)
- **Infrastructure**: [04-DEPLOYMENT.md](./04-DEPLOYMENT.md#deployment-architecture)
- **Monitoring**: [04-DEPLOYMENT.md](./04-DEPLOYMENT.md#monitoring-and-logging)
- **Troubleshooting**: [04-DEPLOYMENT.md](./04-DEPLOYMENT.md#troubleshooting)

### For Database Admins

- **Schema Design**: [05-DATABASE.md](./05-DATABASE.md)
- **Access Patterns**: [05-DATABASE.md](./05-DATABASE.md#access-patterns)
- **Security**: [05-DATABASE.md](./05-DATABASE.md#security-and-access-control)
- **Backup**: [05-DATABASE.md](./05-DATABASE.md#backup-and-recovery)

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Users                                │
│              (Employees, Visitors, Candidates)              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Application Load Balancer                  │
│                     (Port 80 - HTTP)                        │
└──────────┬──────────────────────────┬───────────────────────┘
           │                          │
           ▼                          ▼
┌──────────────────────┐    ┌──────────────────────┐
│   Frontend Service   │    │   Backend Service    │
│   (Next.js + React)  │◄───┤     (FastAPI)        │
│   Port 3000          │    │     Port 8000        │
│   CPU: 512           │    │     CPU: 512         │
│   Memory: 1GB        │    │     Memory: 1GB      │
└──────────────────────┘    └──────────┬───────────┘
                                       │
                                       ▼
                            ┌──────────────────────┐
                            │   Agent Worker       │
                            │   (LiveKit Agent)    │
                            │   CPU: 1024          │
                            │   Memory: 2GB        │
                            └──────────┬───────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────┐
        │                              │                          │
        ▼                              ▼                          ▼
┌───────────────┐            ┌──────────────────┐      ┌──────────────────┐
│   DynamoDB    │            │       S3         │      │  External APIs   │
│   - Employees │            │  - Face Images   │      │  - LiveKit Cloud │
│   - Visitors  │            │  - Visitor Photos│      │  - Google API    │
│   - Managers  │            │  - Company Info  │      │  - AWS SNS       │
└───────────────┘            └──────────────────┘      └──────────────────┘
```

---

## 🌟 Key Features

### 🎤 Conversational AI
- Real-time voice interactions using LiveKit
- Google Gemini 2.0 Flash for natural language understanding
- Multi-turn conversations with context awareness
- Wake word detection ("Hey Clara")

### 🌍 Multi-language Support
- English, Hindi, Tamil, Telugu
- Automatic language detection using FastText
- Dynamic language switching
- Localized responses and UI

### 👤 Face Recognition
- Employee verification using face encodings
- 95%+ accuracy threshold
- Secure storage in S3
- Fast matching with dlib

### 📱 Visitor Management
- Complete visitor registration flow
- Photo capture and storage
- Host notification via SMS
- Check-in/check-out tracking

### 🔐 Security
- OTP-based verification
- Face recognition authentication
- Encrypted data storage
- IAM-based access control

---

## 🚀 Technology Stack

### Frontend
- **Framework**: Next.js 15.5.2
- **UI**: React 19, TailwindCSS 4
- **Real-time**: LiveKit Client SDK
- **Components**: Radix UI, Shadcn/ui

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Real-time**: LiveKit Server SDK
- **Face Recognition**: face_recognition, dlib
- **Language Detection**: FastText

### Agent
- **Framework**: LiveKit Agents SDK
- **LLM**: Google Gemini 2.0 Flash
- **STT/TTS**: Google Speech APIs
- **Plugins**: Noise cancellation

### Infrastructure
- **Compute**: AWS ECS Fargate
- **Database**: Amazon DynamoDB
- **Storage**: Amazon S3
- **Messaging**: AWS SNS
- **Monitoring**: CloudWatch
- **Registry**: Amazon ECR

---

## 📊 Project Statistics

- **Total Lines of Code**: ~15,000+
- **Frontend Components**: 20+
- **Backend Endpoints**: 15+
- **Agent Function Tools**: 8+
- **Supported Languages**: 4
- **DynamoDB Tables**: 3
- **S3 Buckets**: 3
- **AWS Services**: 10+

---

## 🎯 Use Cases

### 1. Employee Check-in
```
User: "Hey Clara"
Clara: "Hello! How may I help you?"
User: "I'm here to check in"
Clara: "Please look at the camera for verification"
[Face recognition]
Clara: "Welcome back, Rakesh! Have a great day!"
```

### 2. Visitor Registration
```
User: "Hi, I'm here for a meeting"
Clara: "Welcome! May I have your name?"
User: "John Doe from ABC Corporation"
Clara: "Who are you here to meet?"
User: "Rakesh Kumar"
Clara: "Thank you! I've notified Rakesh. Please wait in the lobby."
```

### 3. Company Information
```
User: "Tell me about Info Services"
Clara: "Info Services is a leading IT solutions provider..."
User: "What services do you offer?"
Clara: "We offer software development, cloud solutions..."
```

### 4. Multi-language Interaction
```
User: "नमस्ते" (Hindi: Hello)
Clara: "नमस्ते! मैं क्लारा हूं। मैं आपकी कैसे मदद कर सकती हूं?"
User: "मुझे कंपनी के बारे में बताओ"
Clara: "इन्फो सर्विसेज एक प्रमुख आईटी समाधान प्रदाता है..."
```

---

## 🔧 Development Setup

### Prerequisites
- Node.js 18+ and pnpm
- Python 3.11+
- AWS Account
- LiveKit Cloud account
- Google Cloud API key

### Quick Start

```bash
# 1. Clone repository
git clone <repository-url>
cd clara-V2-add-Languages

# 2. Set up environment
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

# 5. Access application
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
```

---

## 📝 Documentation Conventions

### Code Examples
- All code examples are tested and working
- Environment variables are clearly marked
- Comments explain complex logic

### Commands
- Bash commands for Linux/Mac
- PowerShell commands for Windows
- AWS CLI commands include region

### Architecture Diagrams
- Mermaid diagrams for flows
- ASCII art for simple structures
- Clear component relationships

---

## 🤝 Contributing

When contributing to documentation:

1. **Keep it clear**: Use simple language
2. **Add examples**: Include code snippets
3. **Update diagrams**: Keep visuals current
4. **Test commands**: Verify all commands work
5. **Cross-reference**: Link related sections

---

## 📞 Support

For questions or issues:

- **Technical Issues**: Check [04-DEPLOYMENT.md](./04-DEPLOYMENT.md#troubleshooting)
- **Architecture Questions**: See [00-OVERVIEW.md](./00-OVERVIEW.md)
- **API Documentation**: Refer to [02-BACKEND.md](./02-BACKEND.md)
- **Agent Behavior**: Check [03-AGENT.md](./03-AGENT.md)

---

## 📅 Version History

- **v2.0** (Current) - Multi-language support added
- **v1.5** - Face recognition implemented
- **v1.0** - Initial POC release

---

## 📜 License

Proprietary - Info Services © 2025

---

## 🎓 Learning Path

### For New Developers

1. Start with [00-OVERVIEW.md](./00-OVERVIEW.md) to understand the system
2. Read [01-FRONTEND.md](./01-FRONTEND.md) to learn the UI
3. Study [02-BACKEND.md](./02-BACKEND.md) for API details
4. Explore [03-AGENT.md](./03-AGENT.md) for AI implementation
5. Review [05-DATABASE.md](./05-DATABASE.md) for data models

### For DevOps Engineers

1. Read [00-OVERVIEW.md](./00-OVERVIEW.md) for architecture
2. Study [04-DEPLOYMENT.md](./04-DEPLOYMENT.md) thoroughly
3. Review [05-DATABASE.md](./05-DATABASE.md) for data infrastructure
4. Set up monitoring and alerts
5. Practice disaster recovery procedures

---

## 🔗 External Resources

- [LiveKit Documentation](https://docs.livekit.io/)
- [Next.js Documentation](https://nextjs.org/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)

---

**Ready to get started?** Begin with [00-OVERVIEW.md](./00-OVERVIEW.md)!
