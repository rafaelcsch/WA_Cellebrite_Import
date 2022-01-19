# -*- coding: utf-8 -*-

"""
forked from spi_ufed_whatsapp_email.py - 2018 Alberto Magno <alberto.magno@gmail.com> 
Version: 1.0
Revised Date: 19/01/2022
Author: Rafael Schneider <rafaelschneider@igp.sc.gov.br>
License: MIT

# known bugs
# - caracteres especiais em nome de arquivos - ()$
# - outros idiomas - ingles principalmente para dual app ou mods
# - adicionar arquivo .txt como fonte da mensagem instantanea
# - code refactoring
"""


from physical import *
import time, codecs, time, sys, re, os

class WhatsAppEmailsParser(object):
	chats = []
	contacts = {}
	usuario = UserAccount()
	APP_NAME = 'WhatsApp (EmailExport)'
	
	#formato de datas - primeiro ok para whats em pt-br
	date_patterns = {"datetime_format_1" : "(?P<datetime>\d{2}\/\d{2}\/\d{2}\s{1}\d{1,2}:\d{1,2})", # 00/00/2000 00:00
	                "datetime_format_2" : "(?P<datetime>\d{2}\/\d{2}\/\d{2},\s{1}\d{1,2}:\d{1,2})", # 00/00/2000, 00:00
	                "datetime_format_3" : "(?P<datetime>\d{2}\/\d{2}\/\d{2},\s{1}\d{1,2}:\d{1,2}\s{1}(A|P)M)", # 00/00/00, 00:00 AM
	                "datetime_format_4" : "(?P<datetime>\d{2}\/\d{2}\/\d{4},\s{1}\d{1,2}:\d{1,2})", # 00/00/2000, 00:00
	                "datetime_format_1" : "(?P<datetime>\d{2}\/\d{2}\/\d{4}\s{1}\d{1,2}:\d{1,2})"} # 00/00/2000 00:00
	
	#date_format_1 dd/MM/yyyy HH24:mm #date_format_2 dd/MM/yyyy, HH24:mm #date_format_3 dd/MM/yyyy, HH:mm
	#pattern de mensagem
	message_pattern = "\s{1}-\s{1}(?P<name>(.*?)):\s{1}(?P<message>(.*?))$"
	
	#padrao de acoes
	action_pattern = "\s{1}-\s{1}(?P<action>(.*?))$"
	
	#acoes
	action_strings = {
	"admin": "admin",
	"change_icon": "mudou a imagem deste grupo",
	"change_subject": "mudou o nome de",
	"added": "adicionou",
	"left": "saiu",
	"removed": "removeu",
	"crypto": "criptografia de ponta a ponta",
	"temporary" : "ativou as mensagens temporárias"
	}
	
	#objeto elemento do chat
	class WhatsAppChatElement:
	    #construtor
	    def __init__(self, datetime, name, message, action):
	        matchDateTime = re.match(r'(?P<day>\d{1,2})\/(?P<month>\d{1,2})\/(?P<year>\d{2,4})[,]{0,1}\s{1}(?P<hour>\d{1,2}):(?P<minute>\d{1,2})',datetime)
	        yearPlus = 0
	        
	        if not matchDateTime is None:
	            if (len(matchDateTime.group('year'))==2):
	                yearPlus = 2000
	            dt = DateTime(int(matchDateTime.group('year'))+yearPlus,int(matchDateTime.group('month')),int(matchDateTime.group('day')),int(matchDateTime.group('hour')),int(matchDateTime.group('minute')),0)
	            self.datetime = TimeStamp(dt)
	        #datetime_format_3 HH12 AM - PM
	        else:
	            matchDateTime = re.match(r'(?P<day>\d{2})\/(?P<month>\d{2})\/(?P<year>\d{2}),\s{1}(?P<hour>\d{1,2}):(?P<minute>\d{1,2})\s[1](?P<ampm>((A|P)M))',datetime)
	            if not matchDateTime is None:
	                HH12 = 0
	                if matchDateTime.group('ampm').contains('P'):
	                    HH12 = 12
	                dt = DateTime(int(matchDateTime.group('year'))+2000,int(matchDateTime.group('month')),int(matchDateTime.group('day')),int(matchDateTime.group('hour'))+HH12,int(matchDateTime.group('minute')),0)
	                self.datetime = TimeStamp(dt)
	        
	        self.name = name
	        self.message = message
	        self.action = action
	
	
	#construtor
	def __init__(self):
		self.chats=[]
	
	#primeira funcao chamada para executar
	def parse(self):	
		results = []
		#try to read account file - ok working
		self.parseAccount()
		#chama decodificacao das mensagens
		self.decode_messages()
		#chama decodificacao das mensagens de grupos
		self.decode_groups_messages()
		return self.chats
	
	#ok - ver: cria numero de telefone como low confidence
	def createContact(self, number, name): 		
		contact = Contact()
		contact.Account.Value = self.usuario.Username.Value
		contact.Name.Value = name
		contact.Deleted = DeletedState.Intact
		contact.Source.Value = self.APP_NAME
		contact.InteractionStatuses.Add(ContactType.ChatParticipant)
		ph = PhoneNumber()
		ph.Deleted = DeletedState.Intact
		ph.Value.Value = number.split("@")[0][2:]
		ph.Category.Value = 'Telefone'
		contact.Entries.Add(ph)
		uid = UserID()
		uid.Category.Value = 'WhatsApp User Id'
		uid.Value.Value = number
		uid.Deleted = DeletedState.Intact
		contact.Entries.Add(uid)
		#a ver esse parametro
		self.contacts[contact.Name.Value] = contact.Account.Value
		ds.Models[Contact].Add(contact)
	
	def createUserAccount(self, number, name, app):
		self.APP_NAME = app + ' (EmailExport)'
		ua = UserAccount()
		ua.Name.Value = name
		ua.Username.Value = number + '@s.whatsapp.net'
		ua.ServiceType.Value = self.APP_NAME
		ua.Deleted = DeletedState.Intact
		ph = PhoneNumber()
		ph.Deleted = DeletedState.Intact
		ph.Value.Value = number
		ua.Entries.Add(ph)
		#a ver esse parametro
		self.usuario = ua
		ds.Models.Add(ua)
	
	#objeto que decodifica as mensagens
	class WhatsApp_Email_Parser:
	    
	    #processa uma linha - recebe a si e a linha para decodificar
	    def parse_message(self,str):
	        #regex de patterns de mensagens e datas
	        for pattern in map(lambda x : x + WhatsAppEmailsParser.message_pattern, WhatsAppEmailsParser.date_patterns.values()):
	            m = re.search(pattern, str)
	            if m:
	                #print ('MSG: %s' % m.group('datetime'))
	                #print ('MSG: %s' % m.group('name'))
	                #print ('MSG: %s' % m.group('message'))
	                #retorna data, nome e mensagem, nenhuma acao
	                return (m.group('datetime'), m.group('name'), m.group('message'), None)
	        
	        # if code comes here, message is continuation or action
	        for pattern in map(lambda x : x + WhatsAppEmailsParser.action_pattern, WhatsAppEmailsParser.date_patterns.values()):
	            m = re.search(pattern, str)
	            if m:
	                #se encontrou o padrao de data mensagem
	                for pattern in map(lambda x: x, WhatsAppEmailsParser.action_strings.values()):
	                    m_action = re.search(pattern, m.group('action'))
	                    #if m_action:
	                    #    print(m_action)
	                    #    print("mensagem de sistema encontrada")
	                    return (m.group('datetime'), "System Message", None, m.group('action'))
	                    #print("[erro em capturar a acao - necessario verificar] - %s\n" %(m.group('action')))
	                    #return (m.group('datetime'), None, None, m.group('action'))
	        
	        #controle
	        #print ("continuacao ou nao esta no padrao")
	        #prone to return invalid continuation if above filtering doesn't cover all patterns for messages and actions
	        return (None, None, str, None)
	    
	    #processa a mensagem
	    def process(self, content):
	        messages = []
	        #cria objeto vazio - datetime, name, message, action
	        null_chat = WhatsAppEmailsParser.WhatsAppChatElement('', '', '', '')
	        
	        #anexa a mensagens
	        messages.append(null_chat)
	        #contador de linhas
	        row_count = 0
	        
	        #para cada linha no conteudo do arquivo 
	        for row in content:
	            #print (row)
	            parsed = self.parse_message(row)
	            #print(parsed)
	            if parsed[0] is None:
	                #print ("row: %s appended" % row_count)
	                if not messages[-1].message is None:
	                    messages[-1].message += parsed[2]
	                else:
	                    messages[-1].message = parsed[2]
	            else:
	                #print ("parsed message")
	                messages.append(WhatsAppEmailsParser.WhatsAppChatElement(parsed[0],parsed[1],parsed[2], parsed[3]))			
	            row_count = row_count + 1
	            #print(parsed)
	        #print ('Total: %d' % row_count)
	        messages.remove(null_chat)
	        return messages
	    
	    
	#decodifica as mensagens
	def decode_messages(self):
		#pega a lista de arquivos com match de nome
		arquivos = []
		node = ds.FileSystems[0]
		for f in node.Search ('/.*?/CHAT_[0-9]*@s\.whatsapp\.net\.txt'):
			n= re.match(r'/Conversa do WhatsApp com (?P<Name>.*)/CHAT_(?P<Numero>[0-9]*@s\.whatsapp\.net)\.txt', f.AbsolutePath)    #ok
			#print (n.group('Numero'), n.group('Name'))
			self.createContact(n.group('Numero'), n.group('Name'))
			arquivos.append(f)  #ok
		
		for f in arquivos:
			#controla os participantes deste chat
			chat_participantes = {}
			
			#usuario sempre eh um participante do chat
			chat_participantes[self.usuario.Name.Value] = self.usuario.Username.Value
			user_party = Party()
			user_party.Identifier.Value = self.usuario.Username.Value
			user_party.Name.Value = self.usuario.Name.Value
			
			#novo objeto chat, estado nao excluido
			chat = Chat()
			chat.Deleted = DeletedState.Intact
			
			#match com nome do arquivo
			rchat_name_parser = re.match(r'/Conversa do WhatsApp com (?P<Name>.*)/CHAT_(?P<Numero>[0-9]*@s\.whatsapp\.net)\.txt', f.AbsolutePath)
			chat.Id.Value = (rchat_name_parser.group('Numero')).split("@")[0][2:]
			chat.Source.Value = self.APP_NAME
			chat.Participants.Add(user_party)
			
			#adiciona o outro participante
			second_party = Party()
			second_party.Name.Value = rchat_name_parser.group('Name')
			chat_participantes[rchat_name_parser.group('Name')] = rchat_name_parser.group('Numero')
			second_party.Identifier.Value = chat_participantes[rchat_name_parser.group('Name')]
			chat.Participants.Add(second_party)
			
			ws_parser = self.WhatsApp_Email_Parser()
			#carrega conteudo do arquivo e divide por linhas
			text = f.Data.read().decode('utf-8-sig', 'ignore')
			content = text.splitlines()
			
			ancient_date = time.localtime() #today
			recent_date = TimeStamp.FromUnixTime(0) # pre nintendo era
			
			#print("arquivo")
			#testando aqui
			for m in ws_parser.process(content):
				#print("foi uma mensagem")
				#print (m)
				im = InstantMessage()
				im.Deleted = DeletedState.Intact
				#link para fonte - pendente
				#im.SourceInfo = ModelSourceInfo(None, f)
				#se nao eh acao
				if m.action is None:
					#corpo da mensagem recebe mensagem
					im.Body.Value = m.message
					#verifica se tem anexo
					anexo_parser = re.match(r'(.*)\s\(arquivo anexado\)'.decode('UTF-8', 'ignore'), m.message)
					#print m.message
					#.{1}(.*)\s\(arquivo anexado\)
					if not anexo_parser is None: #has attachement
						#print(anexo_parser.group(1))
						att = Attachment()
						nome_anexo = ''
						#funcao usada em caso de caracter especial exportado antes do nome do arquivo.-  impede vincular o anexo
						#print anexo_parser.group(1).find('‎') 
						if anexo_parser.group(1).find('‎') < 0:
						    nome_anexo = anexo_parser.group(1)
						else:
						    nome_anexo = anexo_parser.group(1)[1:]
						
						att.Filename.Value = nome_anexo
						#print (att.Filename.Value)
						att.Deleted = DeletedState.Intact
						#procura arquivo no projeto - necessario testar no PA
						controle = []
						for anexo in node.Search (att.Filename.Value):
							#print (anexo.AbsolutePath)
							controle.append(anexo)
							att.Data.Source = anexo.Data
							im.Attachments.Add(att)
						if(len(controle) == 0):
							print ("!!!WARNING!!! Attachment file not found: %s : chat com %s" % (anexo_parser.group(1), rchat_name_parser.group('Name')))
					
					#midia nao exportada ou ausente
					anexo_ausente = re.match(r'(<M(.*)dia omitida>)|(<Arquivo de m(.*)dia oculto>)|(<media omitted>)', m.message)
					if not anexo_ausente is None: 
						#print ("anexo oculto")
						im.Body.Value = im.Body.Value+" -<O anexo nao foi localizado no dispositivo>"
				else:
					#se eh uma acao	
					im.Body.Value = ("( %s )" % m.action)
				party = Party()
				party.Name.Value = m.name
				#se nao eh mensagem de sistema
				if not m.name == "System Message":
				    #se esse remetente nao esta inserido nos participantes ainda, entao insere
				    if m.name not in chat_participantes:
				        chat_participantes[m.name] = rchat_name_parser.group('Numero')
				        chat.Participants.Add(party)
				    party.Identifier.Value = chat_participantes[m.name]
				#print self.usuario.Name.Value
				if m.name == self.usuario.Name.Value:
				    #party.Role.Value = PartyRole.To
				    im.From.Value = party
				    im.Direction = ModelDirections.Outgoing
				    #print("mensagem do usuario")
				else:
				    #party.Role.Value = PartyRole.From
				    im.From.Value = party
				    im.Direction = ModelDirections.Incoming
				
				#data da mensagem
				im.TimeStamp.Value = m.datetime
				if im.TimeStamp.Value < ancient_date:
					ancient_date = im.TimeStamp.Value
				if im.TimeStamp.Value > recent_date:
					recent_date = im.TimeStamp.Value 
				
				chat.Messages.Add(im)
			chat.StartTime.Value = ancient_date
			chat.LastActivity.Value = recent_date
			#print("chat pronto")
			self.chats.append(chat)
	
		#decodifica as mensagens de grupos
	def decode_groups_messages(self):
		#pega a lista de arquivos com match de nome
		arquivos = []
		node = ds.FileSystems[0]
		for f in node.Search ('/.*?/CHAT_[0-9]*-[0-9]*@g.us.txt'):
			n= re.match(r'/Conversa do WhatsApp com (?P<Name>.*)/CHAT_[0-9]*-[0-9]*@g.us.txt', f.AbsolutePath) #ok
			#nome do grupo
			#print (n.group('Name'))
			arquivos.append(f)  #ok
		
		for f in arquivos:
			#controla os participantes deste chat
			chat_participantes = {}
			
			#usuario sempre eh um participante do chat
			chat_participantes[self.usuario.Name.Value] = self.usuario.Username.Value
			user_party = Party()
			user_party.Identifier.Value = self.usuario.Username.Value
			user_party.Name.Value = self.usuario.Name.Value
			
			#novo objeto chat, estado nao excluido
			chat = Chat()
			chat.Deleted = DeletedState.Intact
			
			#match com nome do arquivo
			rchat_name_parser = re.match(r'/Conversa do WhatsApp com (?P<Name>.*)/CHAT_(?P<Numero>[0-9]*-[0-9]*@g.us).txt', f.AbsolutePath)
			chat.Id.Value = (rchat_name_parser.group('Numero'))
			chat.Name.Value = (rchat_name_parser.group('Name'))
			chat.Source.Value = self.APP_NAME
			chat.Participants.Add(user_party)
			
			ws_parser = self.WhatsApp_Email_Parser()
			#carrega conteudo do arquivo e divide por linhas
			text = f.Data.read().decode('utf-8-sig', 'ignore')
			content = text.splitlines()
			
			ancient_date = time.localtime() #today
			recent_date = TimeStamp.FromUnixTime(0) # pre nintendo era
			
			#print("arquivo")
			#testando aqui
			for m in ws_parser.process(content):
				#print("foi uma mensagem")
				#print (m)
				im = InstantMessage()
				im.Deleted = DeletedState.Intact
				#link para fonte - pendente
				#im.SourceInfo.Nodes = f
				#se nao eh acao
				if m.action is None:
					#corpo da mensagem recebe mensagem
					im.Body.Value = m.message
					#verifica se tem anexo
					anexo_parser = re.match(r'(.*)\s\(arquivo anexado\)'.decode('UTF-8', 'ignore'), m.message)
					#print m.message
					#.{1}(.*)\s\(arquivo anexado\)
					if not anexo_parser is None: #has attachement
						#print(anexo_parser.group(1))
						att = Attachment()
						nome_anexo = ''
						#funcao usada em caso de caracter especial exportado antes do nome do arquivo.-  impede vincular o anexo
						#print anexo_parser.group(1).find('‎') 
						if anexo_parser.group(1).find('‎') < 0:
						    nome_anexo = anexo_parser.group(1)
						else:
						    nome_anexo = anexo_parser.group(1)[1:]
						
						att.Filename.Value = nome_anexo
						#print (att.Filename.Value)
						att.Deleted = DeletedState.Intact
						#procura arquivo no projeto - necessario testar no PA
						controle = []
						for anexo in node.Search (att.Filename.Value):
							#print (anexo.AbsolutePath)
							controle.append(anexo)
							att.Data.Source = anexo.Data
							im.Attachments.Add(att)
						if(len(controle) == 0):
							print ("!!!WARNING!!! Attachment file not found: %s : chat com %s" % (anexo_parser.group(1), rchat_name_parser.group('Name')))
					
					#midia nao exportada ou ausente
					anexo_ausente = re.match(r'(<M(.*)dia omitida>)|(<Arquivo de m(.*)dia oculto>)|(<media omitted>)', m.message)
					if not anexo_ausente is None: 
						#print ("anexo oculto")
						im.Body.Value = im.Body.Value+" -<O anexo nao foi localizado no dispositivo>"
				else:
					#se eh uma acao	
					im.Body.Value = ("( %s )" % m.action)
				party = Party()
				party.Name.Value = m.name
				#se nao eh mensagem de sistema
				if not m.name == "System Message":
				    #se esse remetente nao esta inserido nos participantes ainda, entao insere
				    if m.name not in chat_participantes:
				        #percorre os contatos pelo nome do participante
				        in_contacts = 0
				        for contato in ds.Models[Contact]:
				            if contato.Name.Value == m.name:
				                chat_participantes[m.name] = contato.Entries[1].Value.Value
				                in_contacts = 1
				                break
				        if in_contacts == 0:
				            #neste caso nao ha numero
				            chat_participantes[m.name] = ''
				        chat.Participants.Add(party)
				    party.Identifier.Value = chat_participantes[m.name]
				#print self.usuario.Name.Value
				if m.name == self.usuario.Name.Value:
				    #party.Role.Value = PartyRole.To
				    im.From.Value = party
				    im.Direction = ModelDirections.Outgoing
				    #print("mensagem do usuario")
				else:
				    #party.Role.Value = PartyRole.From
				    im.From.Value = party
				    im.Direction = ModelDirections.Incoming
				
				#data da mensagem
				im.TimeStamp.Value = m.datetime
				if im.TimeStamp.Value < ancient_date:
					ancient_date = im.TimeStamp.Value
				if im.TimeStamp.Value > recent_date:
					recent_date = im.TimeStamp.Value 
				
				chat.Messages.Add(im)
			chat.StartTime.Value = ancient_date
			chat.LastActivity.Value = recent_date
			#print("chat pronto")
			self.chats.append(chat)
	
	
	
	def parseAccount(self):
		node = ds.FileSystems[0]
		nome = ''
		app = ''
		tel = ''
		for f in node.Search ('Conta.txt'):
			text = f.Data.read().decode('utf-8-sig', 'ignore')
			content = text.splitlines()
			for row in content:
			    r = re.match('USUARIO : (?P<name>.*)|TELEFONE : (?P<number>[0-9]*)|APLICATIVO : (?P<app>.*)', row)
			    if (r.group('name') is not None):
			        nome = r.group('name')
			    elif (r.group('number') is not None):
			        tel = r.group('number')
			    elif (r.group('app') is not None):
			        app = r.group('app')
			    else:
			        print('erro ao criar a conta do usuario')
			        return
			self.createUserAccount(tel, nome, app)
    
    
#inicio do script
print ("Starting whatsapp export script")
#para indicativo final do script
startTime = time.time()

#calling the parser for results
results = WhatsAppEmailsParser().parse()
ds.Models.AddRange(results)
print ("Finished - The script took %s seconds !" % format(time.time() - startTime))



