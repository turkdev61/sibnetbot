import asyncio
import logging
import aiohttp
from bs4 import BeautifulSoup

# --- AYARLAR ---
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1490409043540316211/szNRJtsbxU2qGFMvd2tKRF2N1TjmM9lkVJHDFsEBktJUq75fb4ewqT0GAYKs8CTLUc9s"

# Takip edilecek siteler ve kontrol aralıkları (saniye cinsinden)
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

# Loglama Ayarları
logging.basicConfig(
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
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


async def send_discord_notify(session, user_name, target_url, video_count):
    payload = {
        "content": (
            f"@everyone 🚨 **Sibnet'e Yeni Video Eklendi!**\n"
            f"**{user_name}** kullanıcısının sayfasında yeni video tespit edildi! (Toplam: {video_count})\n"
            f"🔗 **Sayfa Bağlantısı:** {target_url}"
        ),
        "username": "Sibnet Takipçisi",
        "allowed_mentions": {"parse": ["everyone"]},
    }
    try:
        async with session.post(DISCORD_WEBHOOK_URL, json=payload) as resp:
            if resp.status == 204 or resp.status == 200:
                logging.info(
                    f"[{user_name}] Discord bildirimi (@everyone) başarıyla gönderildi!"
                )
            else:
                logging.error(
                    f"[{user_name}] Discord Webhook hatası: HTTP {resp.status}"
                )
    except Exception as e:
        logging.error(f"[{user_name}] Discord bildirim hatası: {e}")


async def monitor_target(target):
    user_name = target["name"]
    target_url = target["url"]
    interval = target["interval"]

    logging.info(
        f"[{user_name}] Takip başlatıldı. Kontrol sıklığı: {interval} saniye."
    )
    last_video_count = None

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        while True:
            try:
                async with session.get(
                    target_url, timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    status_code = response.status
                    logging.info(
                        f"[{user_name}] İstek atıldı | HTTP Status: {status_code}"
                    )

                    if status_code == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")

                        # Aranan div elementlerini bul
                        video_cells = soup.find_all(
                            "div",
                            class_="video_cell",
                            attrs={
                                "itemtype": "https://schema.org/VideoObject"
                            },
                        )

                        current_video_count = len(video_cells)

                        if last_video_count is None:
                            last_video_count = current_video_count
                            logging.info(
                                f"[{user_name}] İlk durum kaydedildi. Mevcut video sayısı: {current_video_count}"
                            )

                        elif current_video_count > last_video_count:
                            logging.warning(
                                f"[{user_name}] YENİ VİDEO TESPİT EDİLDİ! Önceki: {last_video_count} -> Yeni: {current_video_count}"
                            )
                            await send_discord_notify(
                                session,
                                user_name,
                                target_url,
                                current_video_count,
                            )
                            last_video_count = current_video_count

                        elif current_video_count < last_video_count:
                            logging.info(
                                f"[{user_name}] Video sayısı azaldı/silindi. Güncel sayı: {current_video_count}"
                            )
                            last_video_count = current_video_count

                        else:
                            logging.info(
                                f"[{user_name}] Yeni bir değişiklik yok."
                            )

                    elif status_code == 403:
                        logging.error(
                            f"[{user_name}] 403 Forbidden! IP engeli veya bot koruması."
                        )
                    elif status_code == 429:
                        logging.error(
                            f"[{user_name}] 429 Too Many Requests! Çok fazla istek atıldı."
                        )

            except Exception as e:
                logging.error(f"[{user_name}] İstek sırasında hata: {e}")

            await asyncio.sleep(interval)


async def main():
    logging.info("Tüm Sibnet Takip Görevleri Başlatılıyor...")
    # İki takibi de aynı anda paralel çalıştırır
    tasks = [monitor_target(target) for target in TARGETS]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
