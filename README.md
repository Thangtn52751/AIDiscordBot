# AIDiscordBot — Gemini + Vercel

Bot Discord dùng Gemini cho chat và đọc ảnh, giữ mention, slash commands, thống kê CS2 và nhắc sinh nhật. Python 3.11+; Docker dùng Python 3.12.

## Chạy local

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Điền DISCORD_TOKEN và GEMINI_API_KEY vào .env
.\.venv\Scripts\python main.py
```

Nếu đã có `.env`, sửa file hiện tại thay vì ghi đè. Thay `OPENAI_API_KEY` bằng `GEMINI_API_KEY`. Model mặc định `gemini-3.5-flash-lite`, đổi bằng `GEMINI_MODEL`. Lấy key tại https://aistudio.google.com/.

Giữ personality trong `bot/personality.txt` và hồ sơ trong `data/user_profiles.json`. Không lưu lịch sử hội thoại giữa các tin nhắn. Ảnh Discord CDN tối đa 8 MB; câu trả lời dài được chia thành các tin nhắn tối đa 2.000 ký tự.

## Deploy Vercel Daemons

Project dùng [Vercel Daemons](https://vercel.com/docs/daemons) duy trì Discord Gateway. Không cần Interactions Endpoint URL hoặc HTTP function. Deployment không có trang web; kiểm tra qua Discord và logs daemon.

1. Import repository vào Vercel. Root Directory là thư mục chứa `vercel.json` và `Dockerfile.bot` (repo này là `AIDiscordBot`). Framework chọn **Other**, dùng build/output từ `vercel.json`.
2. Tạo Redis có lưu trữ bền vững, lấy URL TCP/TLS `rediss://...`, không dùng REST URL. Chọn chính sách không tự loại bỏ key nếu nhà cung cấp cho phép.
3. Đặt Environment Variables cho **Production**: `DISCORD_TOKEN`, `GEMINI_API_KEY`, `REDIS_URL` là bắt buộc. `GEMINI_MODEL` tùy chọn. Thêm `FACEIT_API_KEY` cho các lệnh thống kê. `BIRTHDAY_TIMEZONE` mặc định `Asia/Bangkok`. Docker đặt `BOT_HOST=vercel`; không ghi đè thành `local` trên Vercel. Không upload `.env`.
4. Trong Discord Developer Portal bật **Message Content Intent**. Bot cần quyền xem/gửi tin, embed và đọc lịch sử; thông báo sinh nhật cần Mention Everyone nếu muốn ping mọi người.
5. Dừng bot Railway/local cũ để tránh trả lời trùng. Nếu Railway có sinh nhật mới hơn repo, sao lưu và chuyển bản mới nhất vào `data/birthdays.json` trước lần dùng Redis đầu tiên.
6. Deploy **Production**, hoặc chạy `npx vercel@latest --prod` từ thư mục project sau khi liên kết tài khoản. Daemons chỉ chạy Production, không chạy trong Preview hoặc `vercel dev`.
7. Trong logs `discord-bot`, kiểm tra đăng nhập và đồng bộ slash commands. Thử mention, gửi ảnh và `/birthday_info`.

Một instance chạy tại Singapore (`sin1`). Redis lưu sinh nhật và khóa để các phiên bản cập nhật không cùng nhận tin nhắn. Khi mất khóa, tiến trình đóng Discord. Không dùng chung Redis giữa các bot độc lập vì khóa Gateway dùng tên `aidiscordbot:gateway:leader`.

Lần đầu Redis nhập `data/birthdays.json` bằng SET NX; những lần sau giữ dữ liệu hiện tại. Key mặc định `aidiscordbot:birthdays:v1`, đổi bằng `BIRTHDAY_REDIS_KEY`. Local không có `REDIS_URL` vẫn dùng JSON. Không xóa key để cập nhật dữ liệu.

### Giới hạn hosting

Daemons hiện là public beta, ổ đĩa không bền vững nên Redis là bắt buộc. Theo [Vercel limits](https://vercel.com/docs/daemons/limits), Hobby có 420 GB-hours bộ nhớ/tháng, tính cả lúc chờ. Instance 1 GiB dùng hết khoảng 17,5 ngày; chạy 24/7 cả tháng cần quota/gói phù hợp. Gemini và Redis có quota/chi phí riêng.

Kiểm tra Linux bằng Docker (cần Redis vì image dùng chế độ Vercel):

```sh
docker build -f Dockerfile.bot -t aidiscordbot .
docker run --rm --env-file .env -e BOT_HOST=vercel aidiscordbot
```

## Kiểm tra

```sh
python -X utf8 -m unittest discover -s tests -v
```

Tests dùng mock, không gọi AI thật hay gửi tin Discord. Cấu hình Railway đã được thay bằng Vercel; `main.py` vẫn chạy local.

## FACEIT

Ch? l?y th?ng k? t? FACEIT. D?ng `/faceitstats steam_url:` ho?c `/cs2history steam_url:` v?i SteamID64 ho?c link `/profiles/SteamID64`; ??y ch? l? m? ??nh danh ?? tra FACEIT, kh?ng g?i Steam API. Link t?y ch?nh `/id/...` kh?ng c?n h? tr?. L?nh `/csstats` ?? b?; c?c l?nh ???c ??ng b? l?i khi bot kh?i ??ng.
