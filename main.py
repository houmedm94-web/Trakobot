from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import (
    FloodWait, UserPrivacyRestricted, UserNotMutualContact,
    PeerIdInvalid, ChannelPrivate, UserAlreadyParticipant,
    ChatAdminRequired, UserChannelsTooMuch
)
import asyncio
import time
import logging
from typing import List, Dict, Any

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TransferBot:
    def __init__(self):
        self.client = Client("my_bot", bot_token="8397137180:AAFUnyWVcxgVAyiqrPQvBIRp9wcuxPXxSWs")
        self.is_transferring = False

    async def get_members(self, group_identifier: str) -> List[Dict[str, Any]]:
        """Récupère les membres d'un groupe"""
        members = []
        try:
            async for member in self.client.get_chat_members(group_identifier):
                if not member.user.is_bot and not member.user.is_deleted:
                    members.append({
                        'id': member.user.id,
                        'first_name': member.user.first_name or '',
                        'username': member.user.username
                    })
            return members
        except Exception as e:
            logging.error(f"Erreur membres: {e}")
            return []

    async def add_user_to_group(self, user_data: Dict, target_group: str) -> bool:
        """Ajoute un utilisateur à un groupe"""
        try:
            await self.client.add_chat_members(target_group, user_data['id'])
            return True
        except FloodWait as e:
            await asyncio.sleep(e.value)
            return False
        except Exception:
            return False

    async def transfer_members(self, source_group: str, target_group: str, delay: int = 5) -> Dict[str, Any]:
        """Transfert des membres"""
        if self.is_transferring:
            return {'status': 'error', 'message': 'Transfert déjà en cours'}

        self.is_transferring = True
        start_time = time.time()

        try:
            # Vérification des groupes
            source_chat = await self.client.get_chat(source_group)
            target_chat = await self.client.get_chat(target_group)

            # Récupération des membres
            members = await self.get_members(source_group)
            if not members:
                return {'status': 'error', 'message': 'Aucun membre trouvé'}

            # Transfert
            results = {'total': len(members), 'success': 0, 'failed': 0}
            
            for i, member in enumerate(members, 1):
                if not self.is_transferring:
                    break

                success = await self.add_user_to_group(member, target_group)
                if success:
                    results['success'] += 1
                    logging.info(f"✅ {i}/{len(members)} - {member['first_name']}")
                else:
                    results['failed'] += 1
                    logging.info(f"❌ {i}/{len(members)} - {member['first_name']}")

                if i < len(members):
                    await asyncio.sleep(delay)

            duration = time.time() - start_time
            return {
                'status': 'completed',
                'report': f"✅ Transfert terminé: {results['success']}/{results['total']} succès",
                'duration': duration
            }

        except Exception as e:
            return {'status': 'error', 'message': str(e)}
        finally:
            self.is_transferring = False

# Création du bot
bot_app = TransferBot()

@bot_app.client.on_message(filters.command("start"))
async def start_command(client, message: Message):
    await message.reply("🤖 **Bot de Transfert Actif!**\n\n"
                       "Utilisez: `/transfer @groupe_source @groupe_cible`\n"
                       "Exemple: `/transfer @groupeA @groupeB`")

@bot_app.client.on_message(filters.command("transfer"))
async def transfer_command(client, message: Message):
    try:
        args = message.text.split()
        if len(args) != 3:
            await message.reply("❌ **Usage:** `/transfer @groupe_source @groupe_cible`")
            return

        source_group = args[1]
        target_group = args[2]

        status_msg = await message.reply("🔄 **Démarrage du transfert...**")

        # Lancement du transfert
        result = await bot_app.transfer_members(source_group, target_group, delay=5)

        if result['status'] == 'completed':
            await status_msg.edit(f"✅ **Transfert terminé!**\n\n{result['report']}")
        else:
            await status_msg.edit(f"❌ **Erreur:** {result['message']}")

    except Exception as e:
        await message.reply(f"💥 **Erreur critique:** {e}")

@bot_app.client.on_message(filters.command("stop"))
async def stop_command(client, message: Message):
    bot_app.is_transferring = False
    await message.reply("🛑 **Transfert arrêté**")

# Démarrage du bot
if __name__ == "__main__":
    print("🤖 Démarrage du bot de transfert...")
    bot_app.client.run()
