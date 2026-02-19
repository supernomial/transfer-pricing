# Transfer Pricing Plugin for Claude Cowork

Speed up transfer pricing workflows for consulting and in-house teams. Draft master and local files, review compliance requirements, and manage institutional knowledge — directly inside Claude.

> Built by [Supernomial](https://cowork.supernomial.co)

## Requirements

- [Claude Desktop](https://claude.ai/download) with Cowork enabled
- A Supernomial account and API key — [sign up at cowork.supernomial.co](https://cowork.supernomial.co)

## Install

1. Open Claude Desktop → Cowork → Plugins → **Add marketplace by URL**
2. Paste:
   ```
   https://raw.githubusercontent.com/supernomial/transfer-pricing/main/.claude-plugin/marketplace.json
   ```
3. Save your API key from [cowork.supernomial.co/settings](https://cowork.supernomial.co/settings) to your working folder:
   ```
   your-folder/.supernomial/config.json
   ```
   ```json
   { "api_key": "sk_..." }
   ```

## Commands

| Command | Description |
|---|---|
| `/prepare-local-file` | Full workflow: intake → data → blueprint → HTML previews → PDF |
| `/review-local-file` | Review an existing local file against OECD guidelines |
| `/view-data` | Explore structured entity and transaction records |
| `/view-file` | Browse generated deliverables |

## License

MIT — see [LICENSE](LICENSE)
