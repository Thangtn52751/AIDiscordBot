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

## Chay local

```bash
pip install -r requirements.txt
python main.py
```

Neu muon sua nhanh loi YouTube tren may local:

<<<<<<< ours
```env
YTDLP_COOKIES_FROM_BROWSER=edge
```
=======
- `DISCORD_TOKEN`
- `OPENAI_API_KEY`
- `DISCORD_GUILD_ID`
- `YTDLP_COOKIEFILE`
>>>>>>> theirs

## Railway Volume

Bot da duoc chuan bi de dung Railway Volume, khong can `YTDLP_COOKIE_BASE64`.

### Cach set tren Railway

1. Tao Volume trong Railway
2. Mount volume vao app, vi du: `/data`
3. Upload file `cookies.txt` vao volume
4. Set env:

```env
YTDLP_COOKIEFILE=/data/cookies.txt
DISCORD_TOKEN=...
OPENAI_API_KEY=...
DISCORD_GUILD_ID=...
```

<<<<<<< ours
### Ghi chu

- Tren Railway, uu tien `YTDLP_COOKIEFILE`
- `YTDLP_COOKIES_FROM_BROWSER` chi hop cho local
- Khong commit `cookies.txt` vao repo

## Deploy Railway

Repo nay da co san:

- `railway.json`
- `railpack.json`
- `nixpacks.toml`

Railway se chay bot bang:

```bash
python main.py
```
=======
Neu ban khong muon commit file cookie vao repo, hay dung Railway Volume roi mount file vao mot duong dan co dinh, sau do tro `YTDLP_COOKIEFILE` toi duong dan do.
>>>>>>> theirs
