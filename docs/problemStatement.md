# AI Nutrition Assistant Prototype

## Overview

Build an AI nutrition assistant prototype that answers food, nutrition, and safety questions using structured responses, enforces safety boundaries, and logs unsupported or inconsistent claims for future improvement.

## Brief

Build the prototype of a chatbot that answers questions about food, nutrition, and food safety.

Nothing sits under it yet, so it answers from the model's own memory. It'll make things up, and you'll be writing down what it makes up.

## Where This Goes

Milestone 2 slides a retrieval layer under this same app and turns every invented claim into a cited one.

The interface, endpoints, and response schema stay exactly as they are. You're building the container the citations land in.

## Why This One Comes First

Ask a model how much protein a vegetarian adult needs. The answer arrives in 2 seconds, sounds specific, and comes from nobody.

Ask again tomorrow and the number has moved. Ask what a health authority recommends and it will happily tell you, whether or not that authority ever said it.

Food is a bad place for this to happen. A wrong answer reads exactly like a right one, and almost nobody goes and checks.

## What You Build

### 1. Chat Frontend

A message list, an input box, and a sources panel next to the conversation.

The sources panel stays empty this week. Build it now, since Milestone 2 fills it.

### 2. Backend

A chat endpoint, somewhere to store the conversation, and the model call.

Keep the model call on your server, not in the browser.

### 3. Response Schema

The model returns structured output, not prose.

The response should contain:

- Answer text
- A list of claims
- Each claim should contain:
  - Claim text
  - Source field

Every source comes back as `null` this week. That's deliberate.

You're fixing the contract now so Milestone 2 only has to fill it in.

Parse against the schema and fail when it doesn't parse.

### 4. System Prompt

Write:

- What the assistant does
- How it answers
- How long its answers should be
- What it won't touch

Keep a fixed set of questions and re-run all of them after every prompt change.

Fixing one case while quietly breaking three others is the usual way this goes wrong.

### 5. Scope Limits, Enforced in Code

The assistant should not provide:

- Calorie or weight targets
- Recommendations about what anyone should weigh
- Medical advice

It should decline these questions and point the person to a qualified professional.

A line in the prompt won't hold on its own, so put the check in code as well.

### 6. Deploy

Push the project to GitHub and deploy it using:

- Vercel
- Railway

### 7. The Failure Log

Write 10 questions across these 4 categories:

1. Nutrient requirements
2. Food safety and storage
3. Cooking methods
4. Questions where nobody has a clear answer

Run all 10 questions.

For each response, record:

- Claims stated as fact with nothing behind them
- Numbers that shift between runs
- Sources it cited that you can't find
- Questions it should have declined
- Questions where it hedged into uselessness

Group the failures and count them.

Milestone 2 will run the same 10 questions and compare the results.

Don't hardcode fixes. Just record the failures.

## Tools You Can Use

| Area | Tools |
| --- | --- |
| Frontend and Backend | Next.js or React with FastAPI |
| Scaffolding | Cursor or Anti-gravity |
| Model | Anthropic or OpenAI API |
| Storage | Supabase or Postgres. SQLite is fine too |
| Deployment | Vercel or Railway |

## Model Requirements

Both Anthropic and OpenAI have structured output modes. Use structured outputs rather than parsing prose yourself.

## Rules

- Every response must parse against your schema.
- The schema must include a claims list and a source field for each claim.
- Source fields must stay `null`.
- Scope limits must live in code, not just in the prompt.
- The app must be live at a public URL.
- Failures must be recorded, not patched around.
- Model calls must run behind your backend.

## Before You Submit

### Test for Consistency

Ask the same question 3 times and compare the substance, not the wording.

A number that moves between runs is the thing you most need to catch.

Then run your 10 questions and fill in the failure log.

### Test the Scope Limit

Ask the assistant:

- For a daily calorie target
- What someone with a specific condition should eat

Then:

- Rephrase both questions
- Ask them sideways
- Bring them up again after a few unrelated messages

The assistant should decline every time.

## Submission Requirements

### Share GitHub Link

Your `README` should cover:

- Your system prompt
- The response schema
- What changed across prompt versions and why
- How the scope limit is enforced
- Your tech stack

### Share a Working Prototype Link

The live URL.

### Share Google Drive Link of Demo Video (≤ 3 mins)

Share only if working prototype link is not available and make sure to give view access to everyone. Include:

- One normal question
- One follow-up question
- One refusal
