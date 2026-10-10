# Pokémon TCG Drop Monitor — Starter v1

A free-to-start Discord alert bot for Pokémon TCG news and a small set of product pages.

## What v1 does
- Checks Google News RSS searches for official announcements, release news, restocks, deals, and singles/market chatter.
- Can check a small list of product pages for simple availability phrases and alert when a page appears to transition to available.
- Sends alerts to a Discord channel using an incoming webhook.
- Remembers seen links/statuses so it doesn't repeatedly alert on the same news item.
- Runs from GitHub Actions on a scheduled workflow, nominally every 5 minutes. GitHub notes scheduled jobs can be delayed, so this is not a guaranteed instant/real-time system.

## Important limitations
- RSS/news monitoring is not the same as live inventory monitoring. News feeds can be delayed or omit stories.
- Product-page checks are best-effort text checks. Many retailers render inventory with JavaScript, personalize stock, or block automated requests. This version may miss a restock or flag a false positive.
- v1 does not monitor every card/single price and does not purchase items. Those require approved data sources/APIs and retailer-specific integrations.
- Use only permitted sources, respect retailer terms and rate limits, and don't attempt to bypass queues, CAPTCHAs, or anti-bot controls.
- Don't put account passwords, payment details, or webhook URLs in code or public files.

## Setup (no local coding required)

### 1. Create a Discord channel and webhook
1. In Discord, open the server and channel where alerts should appear.
2. Open **Edit Channel → Integrations → Webhooks** (the exact labels may vary).
3. Create a webhook, choose the channel, and copy its URL.
4. Treat the webhook URL like a password. Do not post it publicly.

### 2. Create a GitHub repository
1. Sign in to GitHub and create a new repository named `pokemon-tcg-drop-monitor`.
2. For a free setup, make it **public** (GitHub Actions usage and limits can change; review GitHub's current plan limits).
3. Upload the files and folders from this starter project, preserving the `.github/workflows/monitor.yml` path.
4. In the repository, open **Settings → Secrets and variables → Actions → New repository secret**.
5. Name the secret `DISCORD_WEBHOOK_URL` and paste the webhook URL as its value.

### 3. Enable the workflow
1. Open **Settings → Actions → General** and make sure Actions are allowed.
2. Ensure workflow permissions allow the workflow to write to the repository contents. The workflow file requests `contents: write`; repository settings may still restrict it.
3. Open the **Actions** tab, select **Pokémon TCG Drop Monitor**, and click **Run workflow** to test it.
4. Check the Discord channel and the run log.

### 4. Add product pages
Edit `products.json` and replace the blank example with a few specific product listing URLs. Example format:

```json
[
  {
    "name": "Product name",
    "url": "https://retailer.example/product-page",
    "in_stock_terms": ["add to cart", "in stock", "available now"],
    "out_of_stock_terms": ["sold out", "out of stock", "currently unavailable"]
  }
]
```

Use real, public product URLs and words actually used on those pages. Keep the list small at first. A page's text can include stock phrases in hidden/recommended-product sections, so verify alerts manually.

### 5. Customize what it tracks
Search terms are in `SEARCHES` near the top of `bot.py`. Edit those phrases to include products, sets, stores, or topics you care about. The bot currently focuses on English-language US news.

## Suggested next upgrades
1. Add a curated retailer list with a dedicated, permitted stock feed/API where available.
2. Add singles price tracking from an authorized market data API, with target prices and price-history storage.
3. Add filters for set names, products, max price, and priority tiers.
4. Add alert buttons or a dashboard linking directly to retailer listings.
5. Add email/phone notifications as a backup.

## Troubleshooting
- **No Discord alerts:** check that the secret is named exactly `DISCORD_WEBHOOK_URL` and the URL is current.
- **Workflow can't push `state.json`:** check repository workflow permissions and branch protection settings.
- **No product restock alerts:** check the run log, product URL, and page wording. Some sites cannot be checked reliably with this simple method.
- **Too many news alerts:** narrow the `SEARCHES` queries or add filtering before sending.
