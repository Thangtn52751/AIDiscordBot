# AIDiscordBot

Bot Discord tich hop AI chat va phat nhac YouTube trong voice channel.

## Tinh nang

- Chat AI voi nguoi dung
- Phat nhac YouTube bang `/play`
- Hang cho nhac, pause, resume, skip, stop

## Bien moi truong

Can thiet:

- `DISCORD_TOKEN`
- `OPENAI_API_KEY`
- `DISCORD_GUILD_ID`

Tuy chon:

- `FFMPEG_PATH`
- `YTDLP_COOKIEFILE`
- `YTDLP_COOKIES_FROM_BROWSER`
- `YTDLP_YOUTUBE_PLAYER_CLIENT`
- `YTDLP_YOUTUBE_PO_TOKEN`

## Chay local

```bash
pip install -r requirements.txt
python main.py
```

Neu muon sua nhanh loi YouTube tren may local:

```env
YTDLP_COOKIES_FROM_BROWSER=edge
```

## Railway Volume

Khong nen commit `cookies.txt` vao repo. Cach on dinh va an toan hon la dung Railway Volume:

1. Tao Volume trong Railway
2. Mount vao `/data`
3. Upload file `cookies.txt` vao volume
4. Set env:

```env
YTDLP_COOKIEFILE=/data/cookies.txt
DISCORD_TOKEN=...
OPENAI_API_KEY=...
DISCORD_GUILD_ID=...
```

## Ghi chu

- Tren Railway, `YTDLP_COOKIES_FROM_BROWSER` khong dung duoc
- `YTDLP_COOKIEFILE` nen tro toi `/data/cookies.txt` neu dung Volume
- `cookies.txt` la secret, khong nen push len GitHub
- Neu cookies van khong du, co the thu them:

```env
YTDLP_YOUTUBE_PLAYER_CLIENT=mweb
YTDLP_YOUTUBE_PO_TOKEN=mweb.gvs+YOUR_PO_TOKEN
```

## Deploy Railway

Repo nay da co san:

- `railway.json`
- `railpack.json`
- `nixpacks.toml`

Railway se chay bot bang:

```bash
python main.py
```
