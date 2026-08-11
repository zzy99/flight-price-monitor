# Flight price monitor

Daily GitHub Actions price checks for:

- `HO1229`: 上海 → 丽江, 2026-09-12
- `MU9703`: 大理 → 上海, 2026-09-18

## Deploy

1. Create an empty GitHub repository and upload this directory.
2. Add repository secrets in **Settings → Secrets and variables → Actions**:
   - `FEISHU_WEBHOOK_URL` — optional Feishu/Lark bot webhook.
   - `WECHAT_WORK_WEBHOOK_URL` — optional WeCom bot webhook.
   - `FLYAI_API_KEY` — optional, unlocks full FlyAI service.
3. Use **Actions → Flight price monitor → Run workflow** to test.

The workflow runs at 09:00 Asia/Shanghai (01:00 UTC), sends a daily report,
and commits the latest price history. Scheduled Actions can be delayed.
