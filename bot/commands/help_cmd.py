from discord.ext import commands

@bot.command(name="help")
async def help_command(ctx):

    help_text = """
📜 **Danh sách lệnh cơ bản**

**!help**  
Để biết mấy cái lệnh cơ bản, không thì cứ như gà mắc tóc.

**!ping**  
Kiểm tra độ phản hồi, cho biết là trợ lý có nhanh nhẹn không.

**!userinfo**  
Biết thông tin người dùng, chứ không phải ai cũng "không có tên".

**!roll**  
Để quăng xúc xắc, cho vui cửa vui nhà chứ không phải lúc nào cũng nghiêm túc.
"""

    await ctx.send(help_text)