# Search for employee with name or any field containing "1307"
aws dynamodb scan --table-name zenith-hr-employees --region us-east-1 --filter-expression "contains(#n, :val) OR contains(position, :val) OR contains(account, :val)" --expression-attribute-names "{\"#n\":\"name\"}" --expression-attribute-values "{\":val\":{\"S\":\"1307\"}}" --limit 5
