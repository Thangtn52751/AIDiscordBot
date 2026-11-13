"""Produce a non-empty static output for the Vercel daemon project."""
from pathlib import Path


PAGE = """<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AIDiscordBot</title>
  <style>
    body { font: 18px/1.6 system-ui, sans-serif; max-width: 640px;
           margin: 12vh auto; padding: 24px; color: #202334; }
    h1 { color: #5865f2; }
  </style>
</head>
<body>
  <main>
    <h1>AIDiscordBot</h1>
    <p>Bot trò chuyện bằng Gemini. Hãy mở Discord để sử dụng bot.</p>
    <p>Trang này chỉ cung cấp thông tin, không hiển thị trạng thái kết nối
       của bot. Kiểm tra bot trong Discord hoặc logs trên Vercel.</p>
  </main>
</body>
</html>
"""


def main() -> None:
    output = Path(__file__).resolve().parents[1] / ".vercel-static"
    output.mkdir(parents=True, exist_ok=True)
    (output / "index.html").write_text(PAGE, encoding="utf-8")
    print("Created .vercel-static/index.html")


if __name__ == "__main__":
    main()
