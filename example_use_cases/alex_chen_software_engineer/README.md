# Try It: Debug Production Safely

## The Story

You're debugging a payment service error. Your logs contain:
- API keys
- Database credentials  
- Customer emails
- Internal URLs

You need to share them in Slack. But you're worried about leaking secrets.

---

## Test It Yourself

### 1. Look at the Problem

Open `production_logs_unsafe.txt` - see all the sensitive data?

### 2. Copy Some Logs

- Select 5-10 lines
- Press Ctrl+C
- Watch for a notification

### 3. Paste in Slack (or any app)

- Open Slack/Discord/etc
- Press Ctrl+V
- **Look at what you pasted**

### 4. Compare

Open `production_logs_safe.txt` - is your paste similar?

---

## Did It Work?

**Questions:**
- Was the sensitive data masked?
- Can you still understand the error?
- Would this help you in real work?
- What didn't work?

Let us know!
