# Database Schema - Clara Virtual Receptionist

## 📋 Overview

Clara uses **Amazon DynamoDB** for data storage with three main tables for employees, visitor logs, and manager visits. Additionally, **Amazon S3** is used for storing images and documents.

---

## 🗄️ DynamoDB Tables

### 1. Employee Table

**Table Name**: `zenith-hr-employees`

**Purpose**: Store employee information and credentials

**Schema**:

```json
{
  "id": "uuid-primary-key",
  "employee_id": "1307",
  "name": "Rakesh Kumar",
  "email": "rakesh@infoservices.com",
  "phone": "+919876543210",
  "department": "Engineering",
  "role": "Senior Developer",
  "manager_id": "1205",
  "manager_name": "John Smith",
  "join_date": "2020-01-15",
  "status": "active",
  "face_encoding_available": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-12-01T00:00:00Z"
}
```

**Primary Key**:
- Partition Key: `id` (String)

**Global Secondary Indexes**:

1. **EmailIndex**
   - Partition Key: `email` (String)
   - Projection: ALL
   - Use Case: Search employees by email

2. **EmployeeIdIndex**
   - Partition Key: `employee_id` (String)
   - Projection: ALL
   - Use Case: Search employees by employee ID

**Access Patterns**:

```python
# Get employee by ID
response = table.get_item(Key={'id': 'uuid'})

# Query by email
response = table.query(
    IndexName='EmailIndex',
    KeyConditionExpression=Key('email').eq('rakesh@infoservices.com')
)

# Query by employee ID
response = table.query(
    IndexName='EmployeeIdIndex',
    KeyConditionExpression=Key('employee_id').eq('1307')
)

# Scan for employees in department
response = table.scan(
    FilterExpression=Attr('department').eq('Engineering') & Attr('status').eq('active')
)
```

---

### 2. Visitor Log Table

**Table Name**: `Clara_visitor_log`

**Purpose**: Track all visitor check-ins and check-outs

**Schema**:

```json
{
  "visit_date": "2025-01-15",
  "visit_id": "uuid-range-key",
  "visitor_name": "John Doe",
  "company": "ABC Corporation",
  "purpose": "Business Meeting",
  "host_name": "Rakesh Kumar",
  "host_employee_id": "1307",
  "phone": "+919876543210",
  "email": "john.doe@abc.com",
  "check_in_time": "2025-01-15T10:30:00Z",
  "check_out_time": "2025-01-15T12:45:00Z",
  "status": "checked_out",
  "photo_url": "s3://clara-visitor-photos/uuid.jpg",
  "badge_number": "V-1234",
  "notes": "Meeting in Conference Room A",
  "created_by": "clara-agent",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T12:45:00Z"
}
```

**Primary Key**:
- Partition Key: `visit_date` (String, format: YYYY-MM-DD)
- Sort Key: `visit_id` (String, UUID)

**Why This Design?**:
- Partition by date allows efficient queries for daily visitor logs
- Sort by visit_id enables chronological ordering within a day
- Supports time-range queries for reporting

**Access Patterns**:

```python
# Get all visitors for a specific date
response = table.query(
    KeyConditionExpression=Key('visit_date').eq('2025-01-15')
)

# Get specific visit
response = table.get_item(
    Key={
        'visit_date': '2025-01-15',
        'visit_id': 'uuid'
    }
)

# Get visitors for date range (requires multiple queries)
dates = ['2025-01-15', '2025-01-16', '2025-01-17']
for date in dates:
    response = table.query(
        KeyConditionExpression=Key('visit_date').eq(date)
    )

# Get active visitors (checked in but not checked out)
response = table.query(
    KeyConditionExpression=Key('visit_date').eq('2025-01-15'),
    FilterExpression=Attr('status').eq('checked_in')
)

# Update check-out time
table.update_item(
    Key={'visit_date': '2025-01-15', 'visit_id': 'uuid'},
    UpdateExpression='SET check_out_time = :time, #status = :status',
    ExpressionAttributeNames={'#status': 'status'},
    ExpressionAttributeValues={
        ':time': '2025-01-15T12:45:00Z',
        ':status': 'checked_out'
    }
)
```

---

### 3. Manager Visit Table

**Table Name**: `Clara_manager_visits`

**Purpose**: Track notifications sent to host employees about visitor arrivals

**Schema**:

```json
{
  "visit_id": "uuid-primary-key",
  "manager_id": "1307",
  "manager_name": "Rakesh Kumar",
  "manager_email": "rakesh@infoservices.com",
  "manager_phone": "+919876543210",
  "visitor_name": "John Doe",
  "visitor_company": "ABC Corporation",
  "notification_sent": true,
  "notification_time": "2025-01-15T10:30:00Z",
  "notification_method": "sms",
  "notification_status": "delivered",
  "response_time": "2025-01-15T10:35:00Z",
  "response_action": "acknowledged",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:35:00Z"
}
```

**Primary Key**:
- Partition Key: `visit_id` (String, UUID)

**Access Patterns**:

```python
# Get notification details for a visit
response = table.get_item(Key={'visit_id': 'uuid'})

# Create notification record
table.put_item(Item={
    'visit_id': 'uuid',
    'manager_id': '1307',
    'manager_name': 'Rakesh Kumar',
    'notification_sent': True,
    'notification_time': '2025-01-15T10:30:00Z',
    'notification_method': 'sms'
})

# Update notification status
table.update_item(
    Key={'visit_id': 'uuid'},
    UpdateExpression='SET notification_status = :status',
    ExpressionAttributeValues={':status': 'delivered'}
)
```

---

## 📦 S3 Buckets

### 1. Employee Images Bucket

**Bucket Name**: `clara-employee-images`

**Purpose**: Store employee face images and encodings

**Structure**:

```
clara-employee-images/
├── Employee_Images/
│   ├── 1307.png
│   ├── 1308.png
│   └── 1309.png
└── Pickle_file/
    └── encoding.pkl
```

**encoding.pkl Format**:

```python
{
    "1307": numpy.array([...]),  # 128-dimensional face encoding
    "1308": numpy.array([...]),
    "1309": numpy.array([...])
}
```

**Access Patterns**:

```python
# Upload employee image
s3_client.put_object(
    Bucket='clara-employee-images',
    Key=f'Employee_Images/{employee_id}.png',
    Body=image_bytes,
    ContentType='image/png'
)

# Download face encodings
response = s3_client.get_object(
    Bucket='clara-employee-images',
    Key='Pickle_file/encoding.pkl'
)
encodings = pickle.loads(response['Body'].read())

# Update encodings
s3_client.put_object(
    Bucket='clara-employee-images',
    Key='Pickle_file/encoding.pkl',
    Body=pickle.dumps(encodings)
)
```

---

### 2. Visitor Photos Bucket

**Bucket Name**: `clara-visitor-photos`

**Purpose**: Store visitor photos captured during registration

**Structure**:

```
clara-visitor-photos/
├── 2025-01-15/
│   ├── uuid-1.jpg
│   ├── uuid-2.jpg
│   └── uuid-3.jpg
├── 2025-01-16/
│   └── uuid-4.jpg
└── ...
```

**Lifecycle Policy**:

```json
{
  "Rules": [
    {
      "Id": "DeleteOldVisitorPhotos",
      "Status": "Enabled",
      "Expiration": {
        "Days": 90
      },
      "Filter": {
        "Prefix": ""
      }
    }
  ]
}
```

**Access Patterns**:

```python
# Upload visitor photo
visit_date = datetime.now().strftime('%Y-%m-%d')
s3_client.put_object(
    Bucket='clara-visitor-photos',
    Key=f'{visit_date}/{visit_id}.jpg',
    Body=photo_bytes,
    ContentType='image/jpeg'
)

# Generate presigned URL for viewing
url = s3_client.generate_presigned_url(
    'get_object',
    Params={
        'Bucket': 'clara-visitor-photos',
        'Key': f'{visit_date}/{visit_id}.jpg'
    },
    ExpiresIn=3600
)
```

---

### 3. Company Info Bucket

**Bucket Name**: `clara-company-info`

**Purpose**: Store company information documents

**Structure**:

```
clara-company-info/
└── Info/
    └── company_info.pdf
```

**Access Patterns**:

```python
# Download company info PDF
response = s3_client.get_object(
    Bucket='clara-company-info',
    Key='Info/company_info.pdf'
)
pdf_content = response['Body'].read()

# Update company info
s3_client.put_object(
    Bucket='clara-company-info',
    Key='Info/company_info.pdf',
    Body=pdf_bytes,
    ContentType='application/pdf'
)
```

---

## 🔄 Data Flow Examples

### Employee Verification Flow

```python
# 1. User provides employee ID
employee_id = "1307"

# 2. Query DynamoDB
table = dynamodb.Table('zenith-hr-employees')
response = table.query(
    IndexName='EmployeeIdIndex',
    KeyConditionExpression=Key('employee_id').eq(employee_id)
)

if response['Items']:
    employee = response['Items'][0]
    
    # 3. Check if face encoding available
    if employee.get('face_encoding_available'):
        # 4. Load encodings from S3
        s3_response = s3_client.get_object(
            Bucket='clara-employee-images',
            Key='Pickle_file/encoding.pkl'
        )
        encodings = pickle.loads(s3_response['Body'].read())
        
        # 5. Get employee's encoding
        employee_encoding = encodings.get(employee_id)
```

### Visitor Registration Flow

```python
# 1. Collect visitor information
visitor_data = {
    'visitor_name': 'John Doe',
    'company': 'ABC Corp',
    'purpose': 'Meeting',
    'host_name': 'Rakesh Kumar',
    'phone': '+919876543210'
}

# 2. Generate visit ID
visit_id = str(uuid.uuid4())
visit_date = datetime.now().strftime('%Y-%m-%d')

# 3. Capture and upload photo
photo_key = f'{visit_date}/{visit_id}.jpg'
s3_client.put_object(
    Bucket='clara-visitor-photos',
    Key=photo_key,
    Body=photo_bytes
)

# 4. Create visitor log entry
visitor_table = dynamodb.Table('Clara_visitor_log')
visitor_table.put_item(Item={
    'visit_date': visit_date,
    'visit_id': visit_id,
    'visitor_name': visitor_data['visitor_name'],
    'company': visitor_data['company'],
    'purpose': visitor_data['purpose'],
    'host_name': visitor_data['host_name'],
    'phone': visitor_data['phone'],
    'check_in_time': datetime.now().isoformat(),
    'status': 'checked_in',
    'photo_url': f's3://clara-visitor-photos/{photo_key}'
})

# 5. Find host employee
employee_table = dynamodb.Table('zenith-hr-employees')
host_response = employee_table.scan(
    FilterExpression=Attr('name').eq(visitor_data['host_name'])
)

if host_response['Items']:
    host = host_response['Items'][0]
    
    # 6. Create manager visit record
    manager_table = dynamodb.Table('Clara_manager_visits')
    manager_table.put_item(Item={
        'visit_id': visit_id,
        'manager_id': host['employee_id'],
        'manager_name': host['name'],
        'manager_phone': host['phone'],
        'visitor_name': visitor_data['visitor_name'],
        'notification_sent': True,
        'notification_time': datetime.now().isoformat()
    })
    
    # 7. Send SMS notification
    sns_client.publish(
        PhoneNumber=host['phone'],
        Message=f"Visitor {visitor_data['visitor_name']} from {visitor_data['company']} is here to meet you."
    )
```

---

## 📊 Data Analytics Queries

### Daily Visitor Report

```python
def get_daily_visitor_report(date: str):
    """Get visitor statistics for a specific date"""
    table = dynamodb.Table('Clara_visitor_log')
    
    response = table.query(
        KeyConditionExpression=Key('visit_date').eq(date)
    )
    
    visitors = response['Items']
    
    return {
        'total_visitors': len(visitors),
        'checked_in': len([v for v in visitors if v['status'] == 'checked_in']),
        'checked_out': len([v for v in visitors if v['status'] == 'checked_out']),
        'by_company': Counter([v.get('company', 'Unknown') for v in visitors]),
        'by_purpose': Counter([v.get('purpose', 'Unknown') for v in visitors])
    }
```

### Employee Verification Statistics

```python
def get_employee_stats():
    """Get employee statistics"""
    table = dynamodb.Table('zenith-hr-employees')
    
    response = table.scan()
    employees = response['Items']
    
    return {
        'total_employees': len(employees),
        'active_employees': len([e for e in employees if e['status'] == 'active']),
        'by_department': Counter([e['department'] for e in employees]),
        'face_encoding_enabled': len([e for e in employees if e.get('face_encoding_available')])
    }
```

---

## 🔒 Security and Access Control

### IAM Policy for Application

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:*:table/zenith-hr-employees",
        "arn:aws:dynamodb:us-east-1:*:table/zenith-hr-employees/index/*",
        "arn:aws:dynamodb:us-east-1:*:table/Clara_visitor_log",
        "arn:aws:dynamodb:us-east-1:*:table/Clara_manager_visits"
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
        "arn:aws:s3:::clara-visitor-photos/*",
        "arn:aws:s3:::clara-company-info/*"
      ]
    }
  ]
}
```

### DynamoDB Encryption

```yaml
# Enable encryption at rest
SSESpecification:
  SSEEnabled: true
  SSEType: KMS
  KMSMasterKeyId: !Ref KMSKey
```

### S3 Bucket Policies

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyUnencryptedObjectUploads",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::clara-employee-images/*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption": "AES256"
        }
      }
    }
  ]
}
```

---

## 🔄 Backup and Recovery

### DynamoDB Point-in-Time Recovery

```bash
# Enable PITR
aws dynamodb update-continuous-backups \
  --table-name zenith-hr-employees \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true

# Restore to specific time
aws dynamodb restore-table-to-point-in-time \
  --source-table-name zenith-hr-employees \
  --target-table-name zenith-hr-employees-restored \
  --restore-date-time 2025-01-15T10:00:00Z
```

### S3 Versioning

```bash
# Enable versioning
aws s3api put-bucket-versioning \
  --bucket clara-employee-images \
  --versioning-configuration Status=Enabled

# List versions
aws s3api list-object-versions \
  --bucket clara-employee-images \
  --prefix Pickle_file/encoding.pkl
```

---

## 📈 Performance Optimization

### DynamoDB Best Practices

1. **Use Batch Operations**:
```python
# Batch write
with table.batch_writer() as batch:
    for item in items:
        batch.put_item(Item=item)
```

2. **Implement Caching**:
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_employee_cached(employee_id: str):
    return get_employee_by_id(employee_id)
```

3. **Use Projection Expressions**:
```python
# Only fetch required attributes
response = table.get_item(
    Key={'id': 'uuid'},
    ProjectionExpression='#name, email, department',
    ExpressionAttributeNames={'#name': 'name'}
)
```

---

**Next**: Read [06-INTEGRATION.md](./06-INTEGRATION.md) for external service integrations.
