# AIDiscordBot

Discord bot có chat AI và đã có chức năng phát nhạc.

## Chuc nang nhac

- `/play <tên bài hát | link YouTube>`: Tìm bài hát và phát nhạc.
- `/queue`: Xem bài hát trong hàng chờ.
- `/pause`: tạm dừng bài hát hiện tại.
- `/resume`: tiếp tục bài hát hoặc tạm dừng.
- `/skip`: Skip bài hát đang phát.
- `/stop`: Dừng nhạc (Bot sẽ rời khỏi voice chat).

## Cai dat them

Cần cài thêm các dependency trong `requirements.txt`:

```bash
pip install -r requirements.txt
```

Bot cần có `FFmpeg` de phat audio. Có 2 cách:

- Cài `ffmpeg` vào `PATH`.
- Hoặc đặt file tại `bin/ffmpeg/ffmpeg.exe`.

Nêu ffmpeg nằm ở vị trí khác, thêm biến môi trường `FFMPEG_PATH`.
