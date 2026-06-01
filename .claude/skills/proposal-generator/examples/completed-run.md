# Example: Completed Proposal Run

## Input (call notes)

```
Client: Jack Fidler, CEO of JFDigital (jack@jfdigital.co.uk)
Problem: Sales team spending 2+ hours per proposal. They have ~8 calls/week and can't scale.
Solution discussed: automate proposal generation from call notes, integrate with their CRM (HubSpot)
Scope: 1) AI proposal generator from call notes → branded PDF/web proposal 2) HubSpot integration — auto-create deal + attach proposal 3) Email sequence triggered on proposal send
Timeline: 4 weeks, wants it done before end of month
Cost agreed: €3,200 (50% deposit upfront)
```

## Extracted Fields (Claude outputs this in Step 2)

```json
{
  "clientFirstName": "Jack",
  "clientLastName": "Fidler",
  "clientCompany": "JFDigital",
  "clientEmail": "jack@jfdigital.co.uk",
  "proposalTitle": "Automated Sales Proposal Engine",
  "descriptionName": "Turn every sales call into a client-ready proposal in under 5 minutes.",
  "oneParagraphProblemSummary": "Your team is spending over 2 hours per proposal — at 8 calls a week, that's a full working day lost to admin. As you scale, this bottleneck only gets worse. You need a system that generates professional proposals automatically, so your team can focus on closing.",
  "solutionHeadingOne": "AI Proposal Generator",
  "solutionDescriptionOne": "Paste call notes and receive a fully formatted, branded web proposal in seconds — ready to send.",
  "solutionIconOne": "zap",
  "solutionHeadingTwo": "HubSpot Automation",
  "solutionDescriptionTwo": "Every proposal automatically creates a deal in HubSpot and attaches the proposal link — zero manual data entry.",
  "solutionIconTwo": "database",
  "solutionHeadingThree": "Follow-Up Sequences",
  "solutionDescriptionThree": "Triggered email sequences fire on proposal send, open, and sign — keeping deals moving without chasing.",
  "solutionIconThree": "mail",
  "shortScopeTitleOne": "Proposal Generator",
  "shortScopeDescriptionOne": "AI-powered system that converts call notes into a branded, hosted proposal page with e-signature and Stripe payment.",
  "shortScopeTitleTwo": "HubSpot Integration",
  "shortScopeDescriptionTwo": "Automated deal creation, proposal attachment, and pipeline stage updates triggered by proposal events.",
  "shortScopeTitleThree": "Email Sequences",
  "shortScopeDescriptionThree": "3-step automated follow-up sequence triggered on proposal send, open, and sign.",
  "milestoneOneDay": "Week 1",
  "milestoneDescriptionOne": "Proposal generator built and tested. Template customised to JFDigital branding.",
  "milestoneTwoDay": "Week 2",
  "milestoneDescriptionTwo": "HubSpot integration live. Deals auto-created on proposal generation.",
  "milestoneThreeDay": "Week 3",
  "milestoneDescriptionThree": "Email sequences built and connected. End-to-end flow tested with real call notes.",
  "milestoneFourDay": "Week 4",
  "milestoneDescriptionFour": "Full QA, handover walkthrough, video documentation delivered.",
  "cost": "€3,200",
  "depositCost": "€1,600",
  "howSoon": "4 weeks",
  "clientRepName": "Jack Fidler",
  "clientRepTitle": "CEO",
  "clientRegistrationNo": "",
  "clientVatNo": "",
  "clientAddress": ""
}
```

## Confirmation shown to user

> **JFDigital** — Jack Fidler
> **Cost:** €3,200 (deposit: €1,600)
> **Scope:**
> 1. Proposal Generator — AI-powered system...
> 2. HubSpot Integration — Automated deal creation...
> 3. Email Sequences — 3-step automated follow-up...
>
> Does this look right?

## Command run

```bash
python "...scripts/generate_proposal.py" --json '{"clientFirstName":"Jack",...}' --payment
```

## Output

```
## Proposal Generated ✓

**Client:** JFDigital — Jack Fidler
**Project cost:** €3,200 (deposit: €1,600)
**Proposal URL:** https://karlis-28774--scaleshift-proposal.modal.run/p/a3f2c1d4-...

Send that link to the client.
```
