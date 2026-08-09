# TBS LPDP Try Out Website Plan

TBS LPDP Try Out Website
Using only Github Pages & Supabase

## Use Case
1. Do exam
2. Review results

## Requirements

### Question generator agent
1. Define the format for LLM to generate the question based on LPDP test format.
2. Developer will ask LLM to store question to @questions/bank, then push to Supabase for backend API fetch requirement

### Front end
Mock the exambrowser UI @exambrowser-ui
1. Mark question as not sure, for user to check it later.
2. Final submission by user manually, or by timer when it exceeds the section's deadline.

### Back end
Provide API for user to do mock test
1. One question may have one image to view
2. Store user session for each action as little as a question: Start, Save Answer, Mark as Not Sure, Finish.

## Reference
https://ruangtes.id/kisi-kisi/lpdp
