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
import sys

# Configuration du logging avancé
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('transfer_log.txt', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

class AdvancedTransferBot:
    def __init__(self, session_name: str = "advanced_transfer_bot"):
        self.client = Client(session_name)
        self.is_transferring = False
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'errors': {}
        }
    
    async def get_group_info(self, group_identifier: str) -> Dict[str, Any]:
        """Récupère les informations détaillées d'un groupe"""
        try:
            chat = await self.client.get_chat(group_identifier)
            members_count = await self.client.get_chat_members_count(chat.id)
            
            return {
                'id': chat.id,
                'title': chat.title,
                'username': chat.username,
                'members_count': members_count,
                'type': chat.type
            }
        except Exception as e:
            logging.error(f"Erreur groupe {group_identifier}: {e}")
            return None
    
    async def get_members_advanced(self, group_identifier: str) -> List[Dict[str, Any]]:
        """Récupère les membres avec filtres avancés"""
        members = []
        try:
            async for member in self.client.get_chat_members(group_identifier):
                user = member.user
                
                # Filtres avancés
                if user.is_bot:
                    continue
                if user.is_deleted:
                    continue
                if user.is_verified:  # Optionnel: exclure les comptes vérifiés
                    continue
                
                member_data = {
                    'id': user.id,
                    'first_name': user.first_name or '',
                    'last_name': user.last_name or '',
                    'username': user.username,
                    'is_premium': user.is_premium,
                    'status': user.status,
                    'dc_id': user.dc_id
                }
                members.append(member_data)
                
            logging.info(f"📊 {len(members)} membres récupérés après filtres")
            return members
            
        except Exception as e:
            logging.error(f"Erreur récupération membres: {e}")
            return []
    
    async def add_user_with_retry(self, user_data: Dict, target_group: str, max_retries: int = 3) -> bool:
        """Ajoute un utilisateur avec système de retry"""
        for attempt in range(max_retries):
            try:
                await self.client.add_chat_members(target_group, user_data['id'])
                return True
                
            except FloodWait as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = e.value + 5
                logging.warning(f"🔄 Tentative {attempt + 1}/{max_retries} - FloodWait {wait_time}s")
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2)
        
        return False
    
    async def transfer_members_advanced(
        self, 
        source_group: str, 
        target_group: str, 
        delay: int = 4,
        batch_size: int = 50,
        batch_delay: int = 60
    ) -> Dict[str, Any]:
        """Transfert massif avec fonctionnalités avancées"""
        
        if self.is_transferring:
            return {'status': 'error', 'message': 'Transfert déjà en cours'}
        
        self.is_transferring = True
        start_time = time.time()
        
        try:
            # Vérification des groupes
            logging.info("🔍 Vérification des groupes...")
            source_info = await self.get_group_info(source_group)
            target_info = await self.get_group_info(target_group)
            
            if not source_info or not target_info:
                return {'status': 'error', 'message': 'Groupes non trouvés'}
            
            logging.info(f"🎯 Source: {source_info['title']} ({source_info['members_count']} membres)")
            logging.info(f"🎯 Cible: {target_info['title']} ({target_info['members_count']} membres)")
            
            # Récupération des membres
            members = await self.get_members_advanced(source_group)
            
            if not members:
                return {'status': 'error', 'message': 'Aucun membre trouvé'}
            
            # Réinitialisation des stats
            self.stats = {
                'total': len(members),
                'success': 0,
                'failed': 0,
                'errors': {},
                'start_time': start_time
            }
            
            # Transfert par lots avec gestion avancée
            for batch_num, i in enumerate(range(0, len(members), batch_size)):
                if not self.is_transferring:
                    break
                    
                batch = members[i:i + batch_size]
                logging.info(f"📦 Lot {batch_num + 1} - {len(batch)} membres")
                
                for j, member in enumerate(batch, 1):
                    if not self.is_transferring:
                        break
                        
                    global_index = i + j
                    user_identifier = member['username'] or f"{member['first_name']} {member['last_name']}".strip()
                    
                    try:
                        success = await self.add_user_with_retry(member, target_group)
                        
                        if success:
                            self.stats['success'] += 1
                            logging.info(f"✅ {global_index}/{len(members)} - {user_identifier}")
                        else:
                            self.stats['failed'] += 1
                            logging.error(f"❌ {global_index}/{len(members)} - {user_identifier} (Échec après retry)")
                            
                    except UserPrivacyRestricted:
                        self.stats['failed'] += 1
                        self.stats['errors']['privacy'] = self.stats['errors'].get('privacy', 0) + 1
                        logging.warning(f"🚫 {user_identifier} - Restrictions de confidentialité")
                        
                    except UserNotMutualContact:
                        self.stats['failed'] += 1
                        self.stats['errors']['not_mutual'] = self.stats['errors'].get('not_mutual', 0) + 1
                        logging.warning(f"🔒 {user_identifier} - Pas de contact mutuel")
                        
                    except UserAlreadyParticipant:
                        self.stats['success'] += 1  # Considéré comme succès
                        logging.info(f"ℹ️ {user_identifier} - Déjà dans le groupe")
                        
                    except UserChannelsTooMuch:
                        self.stats['failed'] += 1
                        self.stats['errors']['too_many_channels'] = self.stats['errors'].get('too_many_channels', 0) + 1
                        logging.warning(f"📺 {user_identifier} - Trop de channels")
                        
                    except ChatAdminRequired:
                        self.stats['failed'] += 1
                        self.stats['errors']['admin_required'] = self.stats['errors'].get('admin_required', 0) + 1
                        logging.error(f"👑 {user_identifier} - Permissions admin requises")
                        return {'status': 'error', 'message': 'Permissions administrateur insuffisantes'}
                        
                    except FloodWait as e:
                        wait_time = e.value + 10
                        logging.warning(f"⏳ FloodWait détecté - Attente {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                        
                    except Exception as e:
                        self.stats['failed'] += 1
                        error_name = type(e).__name__
                        self.stats['errors'][error_name] = self.stats['errors'].get(error_name, 0) + 1
                        logging.error(f"❌ {user_identifier} - {error_name}: {str(e)}")
                    
                    # Délai entre chaque ajout
                    if global_index < len(members):
                        await asyncio.sleep(delay)
                
                # Délai entre les lots (sauf dernier lot)
                if i + batch_size < len(members) and self.is_transferring:
                    logging.info(f"⏸️ Pause entre lots de {batch_delay}s...")
                    await asyncio.sleep(batch_delay)
            
            # Génération du rapport final
            return self._generate_final_report()
            
        except Exception as e:
            logging.error(f"💥 Erreur critique: {e}")
            return {'status': 'error', 'message': f'Erreur critique: {str(e)}'}
        
        finally:
            self.is_transferring = False
    
    def _generate_final_report(self) -> Dict[str, Any]:
        """Génère un rapport détaillé du transfert"""
        duration = time.time() - self.stats['start_time']
        success_rate = (self.stats['success'] / self.stats['total']) * 100 if self.stats['total'] > 0 else 0
        
        report = f"""
📊 RAPPORT DE TRANSFERT AVANCÉ
================================
⏱️ Durée totale: {duration:.2f} secondes
👥 Total membres: {self.stats['total']}
✅ Succès: {self.stats['success']}
❌ Échecs: {self.stats['failed']}
📈 Taux de réussite: {success_rate:.2f}%

📋 ERREURS DÉTAILLÉES:
"""
        for error_type, count in self.stats['errors'].items():
            report += f"  • {error_type}: {count}\n"
        
        if not self.stats['errors']:
            report += "  Aucune erreur spécifique\n"
        
        report += "================================\n"
        
        logging.info(report)
        
        return {
            'status': 'completed',
            'report': report,
            'stats': self.stats,
            'duration': duration,
            'success_rate': success_rate
        }
    
    async def stop_transfer(self):
        """Arrête le transfert en cours"""
        self.is_transferring = False
        logging.info("🛑 Arrêt du transfert demandé")

# Interface utilisateur avancée
async def interactive_transfer():
    bot = AdvancedTransferBot()
    
    async with bot.client:
        print("🤖 BOT DE TRANSFERT AVANCÉ")
        print("=" * 50)
        
        while True:
            print("\n🎮 Options disponibles:")
            print("1. 🚀 Lancer un transfert")
            print("2. 📊 Vérifier les groupes")
            print("3. 🛑 Quitter")
            
            choice = input("\nChoisissez une option (1-3): ").strip()
            
            if choice == '1':
                source = input("Groupe source (@username ou ID): ").strip()
                target = input("Groupe cible (@username ou ID): ").strip()
                delay = input("Délai entre ajouts (défaut: 4): ").strip()
                delay = int(delay) if delay.isdigit() else 4
                
                print(f"\n🎯 Configuration:")
                print(f"Source: {source}")
                print(f"Cible: {target}")
                print(f"Délai: {delay}s")
                print("=" * 30)
                
                confirm = input("Confirmer le transfert? (o/N): ").strip().lower()
                if confirm in ['o', 'oui', 'y', 'yes']:
                    result = await bot.transfer_members_advanced(source, target, delay)
                    print("\n" + result.get('report', 'Transfert terminé'))
                else:
                    print("❌ Transfert annulé")
                    
            elif choice == '2':
                group = input("Groupe à vérifier (@username ou ID): ").strip()
                info = await bot.get_group_info(group)
                if info:
                    print(f"\n📋 Informations du groupe:")
                    print(f"Titre: {info['title']}")
                    print(f"Username: @{info['username']}")
                    print(f"Membres: {info['members_count']}")
                    print(f"Type: {info['type']}")
                else:
                    print("❌ Groupe non trouvé")
                    
            elif choice == '3':
                print("👋 Au revoir!")
                break
            else:
                print("❌ Option invalide")

if __name__ == "__main__":
    # Lancement du bot
    asyncio.run(interactive_transfer())
