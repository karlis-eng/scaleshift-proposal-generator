# ScaleShift — Proposal Generator

Claude Code skill: call transcript → hosted proposal page with e-signature + Stripe deposit.

## Structure
```
.claude/skills/proposal-generator/
  SKILL.md          ← Claude Code skill definition
  reference.md      ← Full setup guide
  examples/
    completed-run.md
  scripts/
    generate_proposal.py
    gmail_utils.py
    serve_proposal.py
    stripe_utils.py
    templates/
      proposal.html
```

## Usage
1. Copy `.claude/skills/` into your Claude Code project root
2. Copy `.env.example` → `.env` and fill in your API keys
3. Run `/proposal-generator` in Claude Code and paste your transcript

## Required env vars
```
STRIPE_API_KEY=sk_live_...
GMAIL_CREDENTIALS_PATH=credentials.json
```

Full guide → [scaleshift.io/resources](https://scaleshift.io/resources)
