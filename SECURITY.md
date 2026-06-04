# Security

## Reporting a vulnerability

If you discover a security issue, **do not open a public GitHub issue**. Email:
📧 **https://github.com/otixe** with subject `[SECURITY]`. Response within 72h.

## What this starter does NOT store

- ❌ AWS access keys, secrets, or session tokens
- ❌ Bedrock API outputs that contain user PII (unless you put them in memory yourself)
- ❌ Bundled credentials, tokens, or sample API keys

## What it DOES handle

The agent operates on three sensitive surfaces:

1. **AWS credentials** — provided via the standard AWS credential chain
   (`~/.aws/credentials`, env vars, IAM role). Never stored or logged by this code.
2. **User messages** — sent to Bedrock and (optionally) written to your Qdrant
   memory collection. Treat memory as you would any user-content database.
3. **Tool inputs/outputs** — passed verbatim between Claude and your Python
   functions. **Validate them**: Claude can put anything in a string field.

### IAM least-privilege

Create a dedicated IAM user/role for agent execution with only:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:Converse"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-*",
        "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-*",
        "arn:aws:bedrock:us-east-1:000000000000:inference-profile/us.anthropic.claude-*"
      ]
    }
  ]
}
```

### Tool input validation

Tools are typed via Python hints, but Claude sees them as JSON Schema and
**may emit malformed inputs**. The starter enforces basic type-conversion via
the schema, but always:

- Validate string content (length, encoding, allowed chars)
- Sanitize before passing to subprocesses, SQL, file paths
- Treat tool input as untrusted user input

### Memory hygiene

Anything `agent.run()` returns gets written to memory if `memory` is configured.
Avoid storing:

- Raw user PII (emails, IDs, phone numbers) — hash or redact first
- Auth tokens or session IDs
- Internal hostnames / IPs unless the threat model permits

## What you should NEVER commit

- Real AWS account IDs, IAM ARNs from your org, real Bedrock inference profile IDs
- Real Qdrant connection strings (`https://*.cloud.qdrant.io/...` with API keys)
- Demo conversations that include private data
- Memory snapshots from production

Pre-commit hooks (`detect-secrets`, `detect-private-key`, `detect-aws-credentials`)
gate this. Run `pre-commit install` after cloning.
