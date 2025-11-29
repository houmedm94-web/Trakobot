from pyrogram import Client
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    # Version simplifiée avec seulement le token
    async with Client(
        "my_bot",
        bot_token="8397137180:AAFUnyWVcxgVAyiqrPQvBIRp9wcuxPXxSWs",
        api_id=2040,  # Valeur par défaut
        api_hash="b18441a1ff607e10a989891a5462e627"  # Valeur par défaut
    ) as app:
        
        me = await app.get_me()
        print(f"✅ Bot connecté: {me.first_name}")
        
        # Garde le bot actif
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
