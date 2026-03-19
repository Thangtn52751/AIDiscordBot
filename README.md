# 🤖 AIDiscordBot

Bot Discord tích hợp **AI chat** và **phát nhạc YouTube trong voice channel**.

---

## ✨ Tính năng

### 💬 Chat AI

* Trò chuyện thông minh với người dùng
* Ghi nhớ ngữ cảnh hội thoại theo từng user
* Dùng OpenAI API

### 🎵 Phát nhạc

* Phát nhạc từ YouTube (tên bài hoặc link)
* Hỗ trợ hàng chờ (queue)
* Điều khiển nhạc trực tiếp bằng slash command

---

## 🎮 Danh sách lệnh

| Lệnh                | Mô tả             |           |
| ------------------- | ----------------- | --------- |
| `/play <tên bài hát | link>`            | Phát nhạc |
| `/queue`            | Xem hàng chờ      |           |
| `/pause`            | Tạm dừng          |           |
| `/resume`           | Tiếp tục          |           |
| `/skip`             | Bỏ qua            |           |
| `/stop`             | Dừng và rời voice |           |

---

## 🧱 Công nghệ sử dụng

* `discord.py`
* `yt-dlp`
* `FFmpeg`
* `OpenAI API`
* Python 3.10+

---

## ⚙️ Cài đặt Local

### 1. Clone repo

```bash
git clone https://github.com/your-repo/AIDiscordBot.git
cd AIDiscordBot
```

### 2. Cài dependencies

```bash
pip install -r requirements.txt
```

### 3. Cài FFmpeg

Có 2 cách:

#### Cách 1: Thêm vào PATH (khuyến nghị)

* Download: https://ffmpeg.org/download.html
* Thêm vào biến môi trường PATH

#### Cách 2: Đặt trong project

```
bin/ffmpeg/ffmpeg.exe
```

Hoặc set:

```env
FFMPEG_PATH=/đường/dẫn/ffmpeg
```

---

## 🔐 Cấu hình biến môi trường

Tạo file `.env`:

```env
DISCORD_TOKEN=your_token
OPENAI_API_KEY=your_openai_key
DISCORD_GUILD_ID=your_guild_id

YTDLP_COOKIEFILE=
YTDLP_COOKIE_BASE64=
```

---

## 🍪 Fix lỗi YouTube (Quan trọng)

Nếu gặp lỗi:

```
Sign in to confirm you're not a bot
```

### ✅ Cách 1: Dùng cookies.txt

```env
YTDLP_COOKIEFILE=/path/to/cookies.txt
```

### ✅ Cách 2: Lấy từ browser (local)

```env
YTDLP_COOKIES_FROM_BROWSER=chrome
```

⚠️ **Railway KHÔNG dùng được cách này**

---

## 🔐 Cách an toàn (Khuyên dùng): Base64 Cookie

### Bước 1: Convert cookies

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\cookies.txt"))
```

### Bước 2: Set biến

```env
YTDLP_COOKIE_BASE64=your_base64_string
```

👉 Bot sẽ tự:

* Decode
* Tạo file tạm
* Gán vào yt-dlp

---

## 🚀 Deploy Railway

### 1. Push code lên GitHub

### 2. Tạo project Railway

* Chọn repo
* Add variables

### 3. Set ENV trên Railway

```env
DISCORD_TOKEN=
OPENAI_API_KEY=
DISCORD_GUILD_ID=
YTDLP_COOKIE_BASE64=
```

### 4. Deploy

Railway đã có sẵn:

* `ffmpeg`
* start command
* auto restart

👉 Nhớ bật:

* ✅ MESSAGE CONTENT INTENT
* ✅ SERVER MEMBERS INTENT (nếu cần)

---

## 🧠 TODO (Có thể mở rộng)

* [ ] Loop nhạc
* [ ] Shuffle queue
* [ ] Hiển thị lyrics
* [ ] Dashboard web quản lý bot
* [ ] Cache bài hát

---

## ❤️ Ghi chú

* Không commit `cookies.txt` lên GitHub
* Dùng `.env` để bảo mật key
* Nên dùng Base64 cookie khi deploy

---

## 📜 License

MIT License

---

## 👨‍💻 Tác giả

Developed by **Thắng Trần Nam** 🚀

---
