# Test querying employee ID 1307 using the EmployeeIdIndex
aws dynamodb query --table-name zenith-hr-employees --region us-east-1 --index-name EmployeeIdIndex --key-condition-expression "employee_id = :id" --expression-attribute-values "{\":id\":{\"S\":\"1307\"}}"
