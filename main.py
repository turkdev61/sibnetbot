import asyncio
import logging
from datetime import datetime
import aiohttp
from bs4 import BeautifulSoup

# --- AYARLAR ---
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1490409043540316211/szNRJtsbxU2qGFMvd2tKRF2N1TjmM9lkVJHDFsEBktJUq75fb4ewqT0GAYKs8CTLUc9s"

TARGETS = [
    {
        "name": "tayfunhasanov",
        "url": "https://video.sibnet.ru/users/tayfunhasanov/video/",
        "interval": 60,  # 1 dakika
    },
    {
        "name": "cizgiustasi",
        "url": "https://video.sibnet.ru/users/cizgiustasi/video/",
        "interval": 600,  # 10 dakika
    },
]

logging.basicConfig(
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://video.sibnet.ru/",
}


async def send_discord_log(session, log_text, has_new_video=False):
    """Discord kanalına log mesajını ve gerekirse @everyone etiketini atar."""
    content = log_text
    if has_new_video:
        content = f"@everyone 🚨 **YENİ VİDEO TESPİT EDİLDİ!**\n{log_text}"

    payload = {
        "content": content,
        "username": "Sibnet Log Botu",
        "allowed_mentions": {"parse": ["everyone"]},
    }
    try:
        async with session.post(DISCORD_WEBHOOK_URL, json=payload) as resp:
            if resp.status not in (200, 204):
                logging.error(f"[Discord Error] HTTP {resp.status}")
    except Exception as e:
        logging.error(f"[Discord Error] {e}")


async def monitor_target(target):
    user_name = target["name"]
    target_url = target["url"]
    interval = target["interval"]

    last_video_count = None

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        while True:
            now_fmt1 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            now_fmt2 = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

            try:
                async with session.get(
                    target_url, timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    status_code = response.status

                    if status_code == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")

                        video_cells = soup.find_all(
                            "div", class_=lambda c: c and "video_cell" in c
                        )
                        current_video_count = len(video_cells)

                        # Birebir istenen log formatı
                        log_msg = f"[{now_fmt1}] INFO: DETAY -> [{user_name}] | Tarih: {now_fmt2} | HTTP Status: {status_code} | Tespit Edilen Video Sayısı: {current_video_count}"

                        logging.info(log_msg)

                        # İlk çalıştırma
                        if last_video_count is None:
                            last_video_count = current_video_count
                            await send_discord_log(
                                session, f"`{log_msg}`", has_new_video=False
                            )

                        # Yeni video eklendiyse
                        elif current_video_count > last_video_count:
                            await send_discord_log(
                                session,
                                f"`{log_msg}`\n🔗 **Sayfa:** {target_url}",
                                has_new_video=True,
                            )
                            last_video_count = current_video_count

                        # Değişiklik yoksa veya azaldıysa (Normal log gönder)
                        else:
                            await send_discord_log(
                                session, f"`{log_msg}`", has_new_video=False
                            )
                            last_video_count = current_video_count

                    else:
                        error_log = f"[{now_fmt1}] ERROR: DETAY -> [{user_name}] | Tarih: {now_fmt2} | HTTP Status: {status_code}"
                        logging.error(error_log)
                        await send_discord_log(
                            session, f"`{error_log}`", has_new_video=False
                        )

            except Exception as e:
                fail_log = f"[{now_fmt1}] ERROR: DETAY -> [{user_name}] | Tarih: {now_fmt2} | İstek Hatası: {e}"
                logging.error(fail_log)
                await send_discord_log(
                    session, f"`{fail_log}`", has_new_video=False
                )

            await asyncio.sleep(interval)


async def main():
    logging.info("Tüm Sibnet Takip Görevleri Başlatılıyor...")
    tasks = [monitor_target(target) for target in TARGETS]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
