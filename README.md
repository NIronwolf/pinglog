# PingLog

> A Telegram bot that pings you throughout the day asking what you're doing
> and logs your replies to a local SQLite database. Runs 24/7 in Docker on
> a home server.

## Features

- Configurable ping interval with per-reply snooze
- Silent mode for sleep / long focus blocks
- XP and streak gamification
- CLI for reviewing your log and exporting data

## Prerequisites

- Python 3.12+
- Docker and Docker Compose
- A Telegram account and a bot token (see Setup)

## Setup

### 1. Clone the repo

    git clone https://github.com/YOUR_USERNAME/pinglog.git
    cd pinglog

### 2. Create a Telegram bot

    1. Open Telegram and search for @BotFather
    2. Send /newbot and follow the prompts
    3. Copy the token it gives you

### 3. Configure environment

    cp .env.example .env
    # Edit .env and paste in your TELEGRAM_TOKEN and TELEGRAM_CHAT_ID

### 4. Run with Docker

    docker compose up -d

### 5. Test it

    Send /start to your bot in Telegram. You should get a welcome message.

## Usage

    pinglog today       # show today's log
    pinglog streak      # current streak and XP
    pinglog export      # dump log to CSV
