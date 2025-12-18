# IntelliWatts
IntelliWatts is a personal cycling coach that parses your training data and generates a weekly training plan for you using ChatGPT.

It is customizable in terms of:
- Training goals
- Weekly training volume
- Available measurements
  - HR measurements
  - Power measurements


# Set-Up
## Required Tokens
### Intervals.icu
Go to `Settings -> Dev --> API-Key` and copy the key into `./env.sh`.

## PostgreSQL Database (Backend)
```bash
sudo apt install postgresql
sudo systemctl start postgresql
```

```bash
# 1st time:
sudo -u postgres -i
psql postgres
```

```sql
CREATE DATABASE intervals;
CREATE USER intervals_user WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE intervals TO intervals_user;
postgresql+psycopg://intervals_user:password@localhost/intervals
```

## OpenAI API Key
1. https://platform.openai.com/api-keys
2. `Create new secret key`