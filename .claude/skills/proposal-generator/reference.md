# Proposal Generator — Field Reference

## Full JSON Schema

| Field | Type | Description |
|---|---|---|
| `clientFirstName` | string | Client's first name |
| `clientLastName` | string | Client's last name |
| `clientCompany` | string | Company name (used in filename, title, template) |
| `clientEmail` | string | Client's email — used for signed agreement notification |
| `proposalTitle` | string | Compelling 4-8 word title specific to their project |
| `descriptionName` | string | One-sentence value proposition tailored to them |
| `oneParagraphProblemSummary` | string | 2-3 sentences describing their problem in their own language |
| `solutionHeadingOne/Two/Three` | string | Name of each solution component |
| `solutionDescriptionOne/Two/Three` | string | 1-2 sentence description per component |
| `solutionIconOne/Two/Three` | string | Lucide icon name — see icons below |
| `shortScopeTitleOne/Two/Three` | string | Deliverable name |
| `shortScopeDescriptionOne/Two/Three` | string | What they get, specifically |
| `milestoneOneDay` → `milestoneFourDay` | string | Labels e.g. `"Week 1"`, `"Day 1-7"`, `"Final"` |
| `milestoneDescriptionOne` → `Four` | string | What happens at each milestone |
| `cost` | string | Total project cost e.g. `"€3,690"` |
| `depositCost` | string | Exactly 50% e.g. `"€1,845"` |
| `howSoon` | string | Client's desired timeframe e.g. `"4 weeks"` |
| `clientRepName` | string | Full name of signer (defaults to first+last) |
| `clientRepTitle` | string | Title e.g. `"CEO"` — empty string if unknown |
| `clientRegistrationNo` | string | Company reg. no. — empty string if unknown |
| `clientVatNo` | string | VAT number — empty string if unknown |
| `clientAddress` | string | Company address — empty string if unknown |

## Lucide Icon Names (use one per solution component)

`zap` `mail` `file-text` `bar-chart-2` `users` `database` `search` `phone` `calendar` `settings` `trending-up` `cpu` `refresh-cw` `link` `message-square` `layout` `target` `layers` `code` `clipboard`

## Proposal Sections (9 pages in template)

1. **Cover** — Company name, proposal title, date
2. **Case Studies** — Static ScaleShift examples (PPCAssist, JFDigital, Bridge Dental)
3. **The Problem** — `oneParagraphProblemSummary`
4. **The Solution** — 3 solution components
5. **Transition** — Static statement on scalable infrastructure
6. **The Scope** — 3 deliverables
7. **Timeline** — 4 milestones in 2×2 grid
8. **Pricing** — 50/50 split, deposit amount prominent
9. **Sign & Pay** — Signature pad + Stripe deposit button
10. **Thank You** — Shown after `?paid=1` redirect from Stripe

## Payment Flow

- Deposit (50%) → Stripe Payment Link created dynamically per proposal
- Client signs → POSTs signature to Modal → redirected to Stripe checkout
- After payment → `?paid=1` → Thank You section shown
- Completion (50%) → generate manually with `stripe_utils.create_completion_payment_link()`

## Prerequisites

### `.env` keys required
```
STRIPE_SECRET_KEY=sk_live_...
MODAL_PROPOSAL_URL=https://karlis-28774--scaleshift-proposal.modal.run
```

### Python packages
```bash
pip install stripe modal
```

### Modal deployment (one-time, already done)
The Modal app at `MODAL_PROPOSAL_URL` is already deployed. Only re-deploy if the server code changes:
```bash
cd ".claude/skills/proposal-generator/scripts"
modal deploy serve_proposal.py
```

## Known Edge Cases

- **Missing cost in transcript**: Always ask before generating — never infer.
- **Stripe amount parsing**: Handles `€1,845`, `1,845`, `1845`, `1845.00`.
- **Currency**: Currently EUR. Change `currency="eur"` in `stripe_utils.py` if billing in USD.
- **Modal Dict persistence**: Proposals stored indefinitely by UUID.
- **Email notification on sign**: Requires `token.json` (Gmail OAuth) in workspace root. Currently optional — Modal sends email automatically if configured with `GMAIL_TOKEN_B64` secret.
