# X posting helper

Local helper for drafting and posting to the `@nzgiftfinder` X account.

## Files

- Script: `scripts/post_to_x.mjs`
- Secrets: `.env` (gitignored)
- Drafts: `drafts/x/*.txt`

## Required `.env` values

```env
X_CONSUMER_KEY=...
X_CONSUMER_SECRET=...
X_ACCESS_TOKEN=...
X_ACCESS_TOKEN_SECRET=...
```

Optional values that can stay in `.env` but are not required by this script:

```env
X_BEARER_TOKEN=...
X_CLIENT_ID=...
X_CLIENT_SECRET=...
```

## Commands

Draft only:

```bash
node scripts/post_to_x.mjs draft "Your post text here"
```

Dry run without posting:

```bash
node scripts/post_to_x.mjs dry-run "Your post text here"
```

Post immediately:

```bash
node scripts/post_to_x.mjs post "Your post text here"
```

## Recommended workflow

1. Draft the post first
2. Review the wording
3. Post only after explicit approval

## Notes

- Enforces the 280-character limit
- Uses OAuth 1.0a user tokens to post as the account
- If X rejects the request, the raw API error is printed
