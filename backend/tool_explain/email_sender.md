# Email Sender Tool

> Source: `src/tools/email_sender.py`

## Purpose

Sends transactional emails through Gmail’s SMTP service using credentials configured in the environment. Exposed as a LiveKit tool so the agent can notify employees or visitors via email.

## Key Functions

- `_build_email_message(...)`: Creates an `EmailMessage` object with optional CC support.
- `send_email_via_gmail(...)`: Logs in to Gmail over SMTP SSL and sends the email, translating low-level errors into runtime exceptions.
- `send_email(...)`: LiveKit tool wrapper that catches exceptions and returns user-friendly responses.

## Inputs

- `to_email` (str): Recipient address.
- `subject` (str): Email subject line.
- `message` (str): Body text.
- `cc_email` (optional str): Carbon copy recipient.

## Outputs

- Returns success text (e.g., “Email sent successfully to …”) or an error string describing why delivery failed.

## Dependencies

- Environment variables `GMAIL_USER` and `GMAIL_APP_PASSWORD` loaded via `config.py`.
- Gmail SMTP endpoint (`smtp.gmail.com:465`).
- Python `smtplib` and `email.message` packages.

## Typical Usage

```text
Agent invokes send_email(context, to_email, subject, message)
→ Tool fetches Gmail credentials, logs in, and sends the message
→ Response string is relayed back to the user.
```

## Error Handling & Edge Cases

- Raises `RuntimeError` when credentials are missing or authentication fails.
- Converts `SMTPAuthenticationError` and `SMTPException` into detailed messages.
- Tool wrapper catches exceptions and returns a friendly failure description.

## Related Files

- `src/tools/config.py` supplies Gmail credentials.
- `src/tools/visitor_management.py` and other flows call this tool when email notifications are needed.
