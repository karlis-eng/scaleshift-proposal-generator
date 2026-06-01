---
name: proposal-generator
description: Generate a personalized Scaleshift sales proposal from a call transcript or notes. Produces a hosted interactive page with e-signature and optional Stripe deposit payment link. Use immediately after a sales call.
allowed-tools: Bash
disable-model-invocation: false
---

You are running the **Proposal Generator** skill. Scripts are in `c:/Users/leila/Documents/AUTOMATION TEMPLATES/SCALESHIFT WORKFLOWS/.claude/skills/proposal-generator/scripts/`.

## Supporting Files
- Full field reference: [reference.md](reference.md)
- Example completed run: [examples/completed-run.md](examples/completed-run.md)

---

## Pre-flight

Check Python packages are installed:

```bash
py -c "import stripe, modal" 2>&1
```

If either is missing: `py -m pip install stripe modal`

---

## Step 1 — Get input

Ask the user for one of:
- A transcript file path (drag + drop into chat, or paste the path)
- Pasted transcript/notes directly in the message

If the user hasn't provided input yet, ask:
> "Paste your call transcript or notes, or give me the path to the transcript file."

---

## Step 2 — Extract fields

Read the transcript and extract all proposal fields yourself. Output the complete JSON below — do not call any script for this step.

Fields to extract (see [reference.md](reference.md) for full schema):
- Client details: first name, last name, company, email
- `proposalTitle` — compelling 4-8 word title for this specific client
- `descriptionName` — one-sentence value proposition
- `oneParagraphProblemSummary` — 2-3 sentences in their own language
- 3× solution components: `solutionHeadingOne/Two/Three`, `solutionDescriptionOne/Two/Three`, `solutionIconOne/Two/Three`
- 3× scope deliverables: `shortScopeDescriptionOne/Two/Three` (description only — no title keys)
- 4× timeline milestones: `milestoneOneDay/TwoDay/ThreeDay/FourDay`, `milestoneDescriptionOne/Two/Three/Four`

**IMPORTANT:** The JSON passed to `--json` must use flat keys exactly as above. Do NOT use nested arrays (`solutionComponents: [...]`, `scopeDeliverables: [...]`) — the script ignores them and deliverables will be blank.
- `cost` — total project cost (e.g. `"€3,690"`) — **ask the user if not in transcript**
- `depositCost` — exactly 50% of cost
- `howSoon` — client's desired timeframe

Go straight to Step 3 — do not show a confirmation or ask "does this look right?". The user iterates after seeing the live proposal.

---

## Step 3 — Generate proposal

Run immediately after extracting fields:

```bash
py "c:/Users/leila/Documents/AUTOMATION TEMPLATES/SCALESHIFT WORKFLOWS/.claude/skills/proposal-generator/scripts/generate_proposal.py" --json '<fieldsJson>' --payment
```

Replace `<fieldsJson>` with the full extracted JSON (single-quoted, all on one line).

**Flags:**
- `--payment` — always include (creates Stripe deposit link)
- `--contract` — only add if user explicitly asks for contract section

The script outputs a JSON line at the end. Parse it for `proposal_url` and `local_path`.

---

## Step 4 — Report back

```
## Proposal Generated ✓

**Client:** [Company] — [First Name] [Last Name]
**Project cost:** [cost] (deposit: [depositCost])
**Proposal URL:** [proposal_url]

Send that link to the client. They can read, sign, and pay the deposit directly from the page.

[If Stripe failed: "⚠️ Stripe link unavailable — proposal is live but no payment button. Check STRIPE_SECRET_KEY."]
[If Modal failed: "⚠️ Proposal saved locally only at [local_path]. Run: modal deploy ... to restore hosting."]
```

---

---

## Step 5 — Create deal in Deals board

After the proposal is live, create a deal at "Proposal Sent" stage. Parse the numeric amount from `cost` (strip €, commas, spaces → integer).

```bash
py "c:/Users/leila/Documents/AUTOMATION TEMPLATES/SCALESHIFT WORKFLOWS/.claude/skills/lead-pipeline/scripts/create-deal.py" \
  --email "<email from fields>" \
  --company "<company from fields>" \
  --deal-name "<company> — <proposalTitle>" \
  --amount <numeric cost> \
  --stage "Proposal Sent" \
  --proposal-url "<proposal_url from Step 3>" \
  --deal-type "One-time"
```

If `MONDAY_DEALS_BOARD_ID` is not set, skip this step silently.

---

## Rules

- Always include `--payment` flag — proposals without deposit buttons don't convert.
- Never modify the proposal HTML template.
- If cost is missing from transcript, always ask before generating — never guess.
- If Modal upload fails, report the local path so the user can open it in a browser.
- Currency defaults to EUR (matches Scaleshift billing). If client is USD, note it.
