# Get more items to see if any have employee_id field
aws dynamodb scan --table-name zenith-hr-employees --region us-east-1 --limit 10
