# Manager Visit Tool

A modern, glassy-styled web application for managing manager visits in DynamoDB.

## Features

✅ **Full CRUD Operations**
- Create new manager visit records
- Read/View all visits in a beautiful table
- Update existing visit information
- Delete visits with confirmation

✅ **Modern UI**
- Glassmorphism design with backdrop blur effects
- Gradient backgrounds and smooth animations
- Fully responsive for mobile and desktop
- Clean, intuitive interface

✅ **AWS Integration**
- Direct connection to DynamoDB
- Secure credential management
- Real-time data synchronization

## Setup Instructions

### 1. Prerequisites
- AWS Account with DynamoDB access
- DynamoDB table named `Clara_manager_visits` with:
  - Partition Key: `employee_id` (String)
  - Sort Key: `visit_date` (String)

### 2. AWS Credentials
You'll need:
- AWS Access Key ID
- AWS Secret Access Key
- AWS Region (e.g., `us-east-1`)
- DynamoDB Table Name

### 3. Usage

1. **Open the Application**
   - Simply open `index.html` in any modern web browser
   - No server or build process required!

2. **Configure AWS Connection**
   - Fill in your AWS credentials in the configuration section
   - Enter your DynamoDB table name
   - Click "Connect to DynamoDB"

3. **Manage Visits**
   - **Add**: Fill the form and click "Save Visit"
   - **Edit**: Click the "Edit" button on any row, modify fields, and save
   - **Delete**: Click the "Delete" button and confirm
   - **Refresh**: Click the "Refresh" button to reload data

## DynamoDB Table Structure

```
Table Name: Clara_manager_visits

Primary Keys:
- employee_id (String) - Partition Key
- visit_date (String) - Sort Key (Format: YYYY-MM-DD)

Attributes:
- manager_name (String) - Optional
- office (String) - Optional
- notes (String) - Optional
```

## Security Notes

⚠️ **Important Security Considerations:**

1. **Credentials**: This is a client-side application. AWS credentials are stored in browser memory only.
2. **Production Use**: For production, consider:
   - Using AWS Cognito for authentication
   - Implementing an API Gateway + Lambda backend
   - Using temporary credentials via STS
3. **IAM Permissions**: Create a dedicated IAM user with minimal permissions:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "dynamodb:PutItem",
           "dynamodb:GetItem",
           "dynamodb:UpdateItem",
           "dynamodb:DeleteItem",
           "dynamodb:Scan",
           "dynamodb:Query"
         ],
         "Resource": "arn:aws:dynamodb:REGION:ACCOUNT_ID:table/Clara_manager_visits"
       }
     ]
   }
   ```

## Troubleshooting

### Connection Issues
- Verify AWS credentials are correct
- Check IAM user has DynamoDB permissions
- Ensure table name matches exactly
- Verify region is correct

### CORS Errors
- DynamoDB SDK should work directly from browser
- If issues persist, check browser console for specific errors

### Data Not Loading
- Click the "Refresh" button
- Check browser console for error messages
- Verify table exists and has data

## Browser Compatibility

✅ Chrome (recommended)
✅ Firefox
✅ Safari
✅ Edge

Requires modern browser with ES6+ support.

## File Structure

```
manager-visit-tool/
├── index.html      # Main HTML file with UI
├── app.js          # JavaScript logic and AWS integration
└── README.md       # This file
```

## Customization

### Changing Colors
Edit the CSS gradients in `index.html`:
```css
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

### Adding Fields
1. Add input field in `index.html` form section
2. Update `app.js` form submission handler
3. Update table columns in HTML and `createTableRow()` function

## Support

For issues or questions:
1. Check browser console for error messages
2. Verify AWS credentials and permissions
3. Ensure DynamoDB table structure matches requirements

---

**Built for Clara Virtual Receptionist System**
