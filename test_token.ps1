$url = "http://clara-alb-dev-141929868.us-east-1.elb.amazonaws.com/get-token?identity=test&room=Clara-room"
Invoke-WebRequest -Uri $url
