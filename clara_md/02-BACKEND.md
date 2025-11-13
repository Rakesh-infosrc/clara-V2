# Backend Architecture - Clara Virtual Receptionist

## 📋 Overview

The Clara backend is a **FastAPI-based** Python application that handles API requests, manages conversation flows, integrates with AWS services, and coordinates between the frontend and the LiveKit agent.

---

## 🏗️ Architecture

### Technology Stack

- **Framework**: FastAPI 0.100+
- **Language**: Python 3.11+
- **Real-time**: LiveKit Server SDK
- **AWS SDK**: boto3 (DynamoDB, S3, SNS)
- **Face Recognition**: face_recognition, dlib
- **Language Detection**: fasttext (lid.176.ftz)
- **Environment**: python-dotenv
- **ASGI Server**: Uvicorn

### Project Structure

```
backend/
├── src/
│   ├── tools/
│   │   ├── company_info.py          # Company information retrieval
│   │   ├── employee_verification.py # Employee lookup and verification
│   │   ├── visitor_management.py    # Visitor registration and logging
│   │   ├── web_search.py            # DuckDuckGo web search
│   │   └── __init__.py
│   ├── agent.py                     # LiveKit agent implementation
│   ├── agent_state.py               # Agent state management
│   ├── flow_manager.py              # Conversation flow state machine
│   ├── main.py                      # FastAPI application entry
│   ├── messages.py                  # Multi-language message templates
│   └── prompts.py                   # Agent prompts and instructions
├── data/
│   ├── agent_state.json             # Persistent agent state
│   └── flow_sessions.json           # Active flow sessions
├── Language_model/
│   └── lid.176.ftz                  # FastText language detection model
├── KMS/
│   └── logs/                        # Application logs
├── requirements.txt
├── Dockerfile
└── main.py                          # Entry point
```

---

## 🎯 Core Components

### 1. FastAPI Application (`main.py`)

Main application entry point with all API endpoints.

**Key Endpoints:**

```python
@app.get("/health")
async def health_check():
    """Health check endpoint for ALB"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/get-token")
async def get_token(room_name: str, participant_name: str):
    """Generate LiveKit access token"""
    token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    token.with_identity(participant_name)
    token.with_name(participant_name)
    token.with_grants(api.VideoGrants(
        room_join=True,
        room=room_name,
    ))
    return {"token": token.to_jwt(), "url": LIVEKIT_URL}

@app.post("/employee_verify")
async def verify_employee(file: UploadFile):
    """Verify employee through face recognition"""
    # Face recognition logic
    pass

@app.post("/otp/send")
async def send_otp(request: OTPRequest):
    """Send OTP via SMS"""
    # OTP generation and SMS sending
    pass

@app.post("/otp/verify")
async def verify_otp(request: OTPVerifyRequest):
    """Verify OTP code"""
    # OTP verification logic
    pass
```

**CORS Configuration:**

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### 2. Flow Manager (`flow_manager.py`)

State machine-based conversation flow management.

**Flow States:**

```python
class FlowState(Enum):
    IDLE = "idle"
    USER_CLASSIFICATION = "user_classification"
    FACE_RECOGNITION = "face_recognition"
    MANUAL_VERIFICATION = "manual_verification"
    CREDENTIAL_CHECK = "credential_check"
    FACE_REGISTRATION = "face_registration"
    EMPLOYEE_VERIFIED = "employee_verified"
    VISITOR_INFO_COLLECTION = "visitor_info_collection"
    VISITOR_FACE_CAPTURE = "visitor_face_capture"
    HOST_NOTIFICATION = "host_notification"
    FLOW_END = "flow_end"
```

**Session Management:**

```python
class FlowSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.current_state = FlowState.IDLE
        self.user_type = None
        self.employee_data = None
        self.visitor_data = {}
        self.verification_attempts = 0
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
    
    def transition_to(self, new_state: FlowState):
        """Transition to a new state"""
        logger.info(f"Session {self.session_id}: {self.current_state} -> {new_state}")
        self.current_state = new_state
        self.last_activity = datetime.now()
```

**Flow Transitions:**

```python
def handle_user_classification(session: FlowSession, user_type: str):
    """Handle user type classification"""
    session.user_type = user_type
    
    if user_type == "employee":
        session.transition_to(FlowState.FACE_RECOGNITION)
    elif user_type == "visitor":
        session.transition_to(FlowState.VISITOR_INFO_COLLECTION)
    else:
        session.transition_to(FlowState.USER_CLASSIFICATION)
    
    save_session(session)
```

---

### 3. Agent State Manager (`agent_state.py`)

Manages agent wake/sleep state and activity tracking.

**State Management:**

```python
class AgentState:
    def __init__(self):
        self.is_awake = False
        self.last_activity = None
        self.session_id = None
        self.language = "en"
        self.auto_sleep_timeout = 60  # seconds
    
    def wake_up(self, session_id: str):
        """Wake up the agent"""
        self.is_awake = True
        self.session_id = session_id
        self.last_activity = datetime.now()
        logger.info(f"Agent woke up for session {session_id}")
    
    def sleep(self):
        """Put agent to sleep"""
        self.is_awake = False
        self.session_id = None
        logger.info("Agent went to sleep")
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()
    
    def check_auto_sleep(self) -> bool:
        """Check if agent should auto-sleep"""
        if not self.is_awake or not self.last_activity:
            return False
        
        idle_time = (datetime.now() - self.last_activity).total_seconds()
        if idle_time > self.auto_sleep_timeout:
            self.sleep()
            return True
        return False
```

**Language Management:**

```python
def set_preferred_language(lang: str):
    """Set user's preferred language"""
    global agent_state
    agent_state.language = lang
    save_agent_state()
    logger.info(f"Language set to: {lang}")

def get_preferred_language() -> str:
    """Get current language preference"""
    return agent_state.language
```

---

### 4. Multi-language Messages (`messages.py`)

Centralized message templates for all supported languages.

**Message Structure:**

```python
MESSAGES = {
    "en": {
        "wake_prompt": "Hello! I'm Clara, your virtual receptionist. How may I help you today?",
        "language_support_affirm": "I can speak English, Hindi, Tamil, and Telugu. Which language would you prefer?",
        "flow_face_recognition_prompt": "Please look at the camera for face verification.",
        "flow_manual_verification_prompt": "Could you please provide your employee ID?",
        "flow_visitor_info_prompt": "Welcome! May I have your name and the purpose of your visit?",
        # ... more messages
    },
    "hi": {
        "wake_prompt": "नमस्ते! मैं क्लारा हूं, आपकी वर्चुअल रिसेप्शनिस्ट। मैं आपकी कैसे मदद कर सकती हूं?",
        "language_support_affirm": "मैं अंग्रेजी, हिंदी, तमिल और तेलुगु बोल सकती हूं। आप कौन सी भाषा पसंद करेंगे?",
        # ... more messages
    },
    "ta": {
        "wake_prompt": "வணக்கம்! நான் கிளாரா, உங்கள் மெய்நிகர் வரவேற்பாளர். நான் உங்களுக்கு எப்படி உதவ முடியும்?",
        # ... more messages
    },
    "te": {
        "wake_prompt": "నమస్కారం! నేను క్లారా, మీ వర్చువల్ రిసెప్షనిస్ట్. నేను మీకు ఎలా సహాయం చేయగలను?",
        # ... more messages
    }
}

def get_message(key: str, lang: str = "en") -> str:
    """Get message in specified language"""
    return MESSAGES.get(lang, MESSAGES["en"]).get(key, MESSAGES["en"].get(key, ""))
```

---

### 5. Employee Verification Tool (`tools/employee_verification.py`)

Handles employee lookup and face recognition.

**Face Recognition:**

```python
async def verify_employee_face(image_bytes: bytes) -> dict:
    """Verify employee through face recognition"""
    try:
        # Load face encodings from S3
        encodings = load_face_encodings_from_s3()
        
        # Load uploaded image
        image = face_recognition.load_image_file(io.BytesIO(image_bytes))
        face_locations = face_recognition.face_locations(image)
        
        if not face_locations:
            return {"success": False, "message": "No face detected"}
        
        # Get face encoding
        face_encodings = face_recognition.face_encodings(image, face_locations)
        
        if not face_encodings:
            return {"success": False, "message": "Could not encode face"}
        
        uploaded_encoding = face_encodings[0]
        
        # Compare with stored encodings
        for emp_id, stored_encoding in encodings.items():
            matches = face_recognition.compare_faces(
                [stored_encoding], 
                uploaded_encoding,
                tolerance=0.5
            )
            
            if matches[0]:
                # Get employee details from DynamoDB
                employee = get_employee_by_id(emp_id)
                return {
                    "success": True,
                    "employee": employee,
                    "confidence": calculate_confidence(stored_encoding, uploaded_encoding)
                }
        
        return {"success": False, "message": "No match found"}
        
    except Exception as e:
        logger.error(f"Face verification error: {e}")
        return {"success": False, "message": str(e)}
```

**Employee Lookup:**

```python
def get_employee_by_id(employee_id: str) -> dict:
    """Get employee details from DynamoDB"""
    table = dynamodb.Table(EMPLOYEE_TABLE_NAME)
    
    response = table.query(
        IndexName='EmployeeIdIndex',
        KeyConditionExpression=Key('employee_id').eq(employee_id)
    )
    
    if response['Items']:
        return response['Items'][0]
    return None

def get_employee_by_email(email: str) -> dict:
    """Get employee details by email"""
    table = dynamodb.Table(EMPLOYEE_TABLE_NAME)
    
    response = table.query(
        IndexName='EmailIndex',
        KeyConditionExpression=Key('email').eq(email)
    )
    
    if response['Items']:
        return response['Items'][0]
    return None
```

---

### 6. Visitor Management Tool (`tools/visitor_management.py`)

Handles visitor registration and logging.

**Visitor Registration:**

```python
async def register_visitor(visitor_data: dict) -> dict:
    """Register a new visitor"""
    try:
        visit_id = str(uuid.uuid4())
        visit_date = datetime.now().strftime("%Y-%m-%d")
        
        visitor_record = {
            "visit_id": visit_id,
            "visit_date": visit_date,
            "visitor_name": visitor_data["name"],
            "company": visitor_data.get("company", ""),
            "purpose": visitor_data.get("purpose", ""),
            "host_name": visitor_data.get("host_name", ""),
            "phone": visitor_data.get("phone", ""),
            "check_in_time": datetime.now().isoformat(),
            "status": "checked_in"
        }
        
        # Save to DynamoDB
        table = dynamodb.Table(VISITOR_LOG_TABLE_NAME)
        table.put_item(Item=visitor_record)
        
        # Upload photo to S3 if provided
        if "photo" in visitor_data:
            upload_visitor_photo(visit_id, visitor_data["photo"])
        
        # Notify host
        await notify_host(visitor_record)
        
        return {
            "success": True,
            "visit_id": visit_id,
            "message": "Visitor registered successfully"
        }
        
    except Exception as e:
        logger.error(f"Visitor registration error: {e}")
        return {"success": False, "message": str(e)}
```

**Host Notification:**

```python
async def notify_host(visitor_record: dict):
    """Notify host about visitor arrival"""
    try:
        host_name = visitor_record["host_name"]
        
        # Get host employee details
        employee = search_employee_by_name(host_name)
        
        if not employee:
            logger.warning(f"Host not found: {host_name}")
            return
        
        # Send SMS notification
        message = f"""
        Visitor Alert:
        {visitor_record['visitor_name']} from {visitor_record['company']}
        is here to meet you.
        Purpose: {visitor_record['purpose']}
        """
        
        send_sms(employee['phone'], message)
        
        # Create manager visit record
        manager_table = dynamodb.Table(MANAGER_VISIT_TABLE_NAME)
        manager_table.put_item(Item={
            "visit_id": visitor_record["visit_id"],
            "manager_id": employee["employee_id"],
            "manager_name": employee["name"],
            "notification_sent": True,
            "notification_time": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Host notification error: {e}")
```

---

### 7. Company Information Tool (`tools/company_info.py`)

Retrieves company information from S3-stored PDF.

**Implementation:**

```python
async def get_company_information(query: str = "") -> str:
    """Get company information from S3 PDF"""
    try:
        # Download PDF from S3
        s3_client = boto3.client('s3')
        response = s3_client.get_object(
            Bucket=COMPANY_INFO_S3_BUCKET,
            Key=COMPANY_INFO_S3_KEY
        )
        
        pdf_content = response['Body'].read()
        
        # Extract text from PDF
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        
        # If specific query, search for relevant section
        if query:
            relevant_section = search_relevant_section(text, query)
            return relevant_section
        
        return text
        
    except Exception as e:
        logger.error(f"Company info retrieval error: {e}")
        # Fallback to web search
        return await search_web(f"Info Services company information {query}")
```

---

### 7.5 Mem0 Memory Integration (Private Employee Scope)

- Private per-employee storage using a composite `user_id` (e.g., `employeeId:employeeName`).
- Employee name is added as Mem0 `ENTITIES` for grouping on the Mem0 dashboard.
- Tools exposed to the agent:
  - `memory_add(information, categories?, custom_categories?, output_format?)`
  - `memory_get_all(limit=20)`
  - `memory_update(memory_id, content)`
  - `memory_delete(memory_id)`
  - `memory_recall(query, limit=5)`
- Web search results are automatically stored for verified employees (no trigger words).
- All operations are scoped to the current verified employee; cross-employee access is blocked by design.

Example: direct client usage with custom categories and v1.1 output

```python
from mem0_client import add_employee_memory

messages = [
    {"role": "user", "content": "Hi, I'm Mark. I mainly code in JavaScript."},
    {"role": "assistant", "content": "Hello Mark! JavaScript is a versatile language."},
    {"role": "user", "content": "I play League of Legends competitively."},
]

custom_categories = [
    {"gaming": "For users interested in video games, including gaming preferences, favorite titles, and gaming setup."},
    {"technology": "Includes content related to tech interests, such as programming languages and hardware preferences."},
]

ok = add_employee_memory(
    messages,
    user_id="mark",  # in Clara this is resolved to a private employee-scoped id
    entities=["Mark"],
    custom_categories=custom_categories,
    output_format="v1.1",
)
```

Example: via agent tool (JSON string for `custom_categories`)

```python
# memory_add(information, categories?, custom_categories?, output_format?)
await memory_add(
    information="I mainly code in JavaScript and play LoL.",
    custom_categories='[{"technology": "Programming interests"}, {"gaming": "Favorite titles and setup"}]',
    output_format="v1.1",
)
```

---

### 8. OTP Management

**OTP Generation and Sending:**

```python
class OTPManager:
    def __init__(self):
        self.otp_store = {}  # In production, use Redis
        self.otp_expiry = 300  # 5 minutes
    
    def generate_otp(self, phone: str) -> str:
        """Generate 6-digit OTP"""
        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        self.otp_store[phone] = {
            "otp": otp,
            "created_at": datetime.now(),
            "attempts": 0
        }
        
        return otp
    
    async def send_otp(self, phone: str) -> bool:
        """Send OTP via AWS SNS"""
        try:
            otp = self.generate_otp(phone)
            
            message = f"Your Clara verification code is: {otp}. Valid for 5 minutes."
            
            sns_client = boto3.client('sns')
            response = sns_client.publish(
                PhoneNumber=phone,
                Message=message,
                MessageAttributes={
                    'AWS.SNS.SMS.SenderID': {
                        'DataType': 'String',
                        'StringValue': AWS_SNS_SENDER_ID
                    },
                    'AWS.SNS.SMS.SMSType': {
                        'DataType': 'String',
                        'StringValue': AWS_SNS_SMS_TYPE
                    }
                }
            )
            
            logger.info(f"OTP sent to {phone}: {response['MessageId']}")
            return True
            
        except Exception as e:
            logger.error(f"OTP send error: {e}")
            return False
    
    def verify_otp(self, phone: str, otp: str) -> bool:
        """Verify OTP code"""
        if phone not in self.otp_store:
            return False
        
        stored = self.otp_store[phone]
        
        # Check expiry
        age = (datetime.now() - stored['created_at']).total_seconds()
        if age > self.otp_expiry:
            del self.otp_store[phone]
            return False
        
        # Check attempts
        if stored['attempts'] >= 3:
            del self.otp_store[phone]
            return False
        
        # Verify OTP
        if stored['otp'] == otp:
            del self.otp_store[phone]
            return True
        
        stored['attempts'] += 1
        return False
```

---

## 🔄 API Endpoints

### Authentication & Tokens

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/get-token` | Generate LiveKit access token |
| GET | `/health` | Health check endpoint |

### Flow Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/flow/start` | Start new conversation flow |
| GET | `/flow/status` | Get current flow status |
| POST | `/flow/transition` | Transition to new state |
| POST | `/set_language` | Set user language preference |

### Employee Verification

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/employee_verify` | Verify employee via face recognition |
| POST | `/notify_agent_verification` | Notify agent of verification result |
| GET | `/employee/{employee_id}` | Get employee details |

### OTP Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/otp/send` | Send OTP to phone number |
| POST | `/otp/verify` | Verify OTP code |

### Signal Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/post_signal` | Post signal for frontend |
| GET | `/get_signal` | Get pending signals |
| POST | `/dispatch` | Dispatch action to agent |

---

## 🗄️ Data Models

### Flow Session

```python
@dataclass
class FlowSession:
    session_id: str
    current_state: FlowState
    user_type: Optional[str]
    employee_data: Optional[dict]
    visitor_data: dict
    verification_attempts: int
    created_at: datetime
    last_activity: datetime
```

### Employee Record

```python
{
    "id": "uuid",
    "employee_id": "1307",
    "name": "Rakesh Kumar",
    "email": "rakesh@infoservices.com",
    "department": "Engineering",
    "role": "Senior Developer",
    "phone": "+919876543210",
    "face_encoding_available": true
}
```

### Visitor Record

```python
{
    "visit_id": "uuid",
    "visit_date": "2025-01-15",
    "visitor_name": "John Doe",
    "company": "ABC Corp",
    "purpose": "Business Meeting",
    "host_name": "Rakesh Kumar",
    "phone": "+919876543210",
    "check_in_time": "2025-01-15T10:30:00",
    "check_out_time": null,
    "status": "checked_in",
    "photo_url": "s3://bucket/visitor-photos/uuid.jpg"
}
```

---

## 🔐 Security

### Environment Variables

```python
# Required environment variables
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
EMPLOYEE_TABLE_NAME = os.getenv("EMPLOYEE_TABLE_NAME")
VISITOR_LOG_TABLE_NAME = os.getenv("VISITOR_LOG_TABLE_NAME")
```

### IAM Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/zenith-hr-employees",
        "arn:aws:dynamodb:*:*:table/Clara_visitor_log"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::clara-employee-images/*",
        "arn:aws:s3:::clara-visitor-photos/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["sns:Publish"],
      "Resource": "*"
    }
  ]
}
```

---

## 🚀 Deployment

### Docker Build

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    cmake \
    build-essential \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn main:app --reload --port 8000
```

---

**Next**: Read [03-AGENT.md](./03-AGENT.md) to understand the LiveKit agent implementation.
