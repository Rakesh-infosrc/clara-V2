# Create EmployeeIdIndex GSI for the zenith-hr-employees table
$gsiUpdate = @'
[
  {
    "Create": {
      "IndexName": "EmployeeIdIndex",
      "KeySchema": [
        {
          "AttributeName": "employee_id",
          "KeyType": "HASH"
        }
      ],
      "Projection": {
        "ProjectionType": "ALL"
      },
      "BillingMode": "PAY_PER_REQUEST"
    }
  }
]
'@

aws dynamodb update-table --table-name zenith-hr-employees --region us-east-1 --attribute-definitions AttributeName=employee_id,AttributeType=S --global-secondary-index-updates $gsiUpdate
