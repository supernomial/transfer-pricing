---
description: Connect your Supernomial API key
argument-hint: "<your API key>"
---

# /setup — Connect Your API Key

This command saves your Supernomial API key so the plugin can authenticate with the server. It does **not** run the subscription check first — the whole point is to set up the key before other commands can validate.

## Steps

### Step 1: Extract the API key

The user's message contains their API key as the argument after `/transfer-pricing:setup`. Extract it.

If no key was provided, tell the user:
> "Please paste your API key after the command, like this: `/transfer-pricing:setup sk_live_abc123...`
> You can get your key at [cowork.supernomial.co/settings](https://cowork.supernomial.co/settings)."

Then stop.

### Step 2: Validate the format

The key must start with `sk_live_`. If it doesn't, tell the user:
> "That doesn't look like a valid API key. Keys start with `sk_live_`. Check your key at [cowork.supernomial.co/settings](https://cowork.supernomial.co/settings)."

Then stop.

### Step 3: Check for a working folder

Verify the user has a folder selected by listing the working directory contents.

- **No folder available**: Tell the user: "Please select a working folder first. Go to the Cowork home screen, click **'Work in a folder'** at the bottom of the input box, select your transfer pricing folder, and then run this command again."
- **Folder available**: Proceed.

### Step 4: Save the key

1. Create the `.supernomial/` directory in the working folder if it doesn't exist
2. Write the following to `.supernomial/config.json`:

```json
{
  "api_key": "sk_live_..."
}
```

Replace `sk_live_...` with the actual key from the user's message.

### Step 5: Verify the key works

Run:

```bash
python3 skills/local-file/scripts/gateway.py validate
```

- **Exit code 0**: Tell the user: "You're all set! Run `/prepare-local-file` to get started."
- **Exit code 1**: Tell the user: "That key didn't work. Please check your key at [cowork.supernomial.co/settings](https://cowork.supernomial.co/settings) and try again."
