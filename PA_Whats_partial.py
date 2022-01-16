# -*- coding: utf-8 -*-


# problemas
# - verificar como sao adicionados os contatos em extrações normais
# - nao faz parsing de grupos
# - nao faz parsing de mensagens de sistema - actions novas
# - testar com emojis nas mensagens e nomes
# - outros idiomas - ingles principalmente para dual app ou mods



from physical import *
import time, codecs, time, sys, re, os

class SPIWhatsAppEmailsParser(object):
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
	"admin": "administrador",
	"change_icon": "icone do grupo alterado",
	"change_subject": "alterado o topico",
	"added": "adicionado",
	"left": "saiu",
	"removed": "removido"
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
		return self.chats
	
	#ok - ver: cria numero de telefone como low confidence
	def createContact(self, number, name): 		
		uid = UserID()
		uid.Deleted = DeletedState.Intact
		uid.Category.Value = self.APP_NAME+ " Id"
		#uid.Category.Value = 'WhatsApp (EmailExport) Id'
		uid.Value.Value = name
		contact = Contact()
		contact.Account.Value = number
		contact.Name.Value = name
		contact.Deleted = DeletedState.Intact
		contact.Source.Value = self.APP_NAME
		#contact.Source.Value = 'WhatsApp (EmailExport)'
		contact.Entries.Add(uid)
		ph = PhoneNumber()
		ph.Deleted = DeletedState.Intact
		ph.Value.Value = number.split("@")[0][2:]
		contact.Entries.Add(ph)
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
	        for pattern in map(lambda x : x + SPIWhatsAppEmailsParser.message_pattern, SPIWhatsAppEmailsParser.date_patterns.values()):
	            m = re.search(pattern, str)
	            if m:
	                #print ('MSG: %s' % m.group('datetime'))
	                #print ('MSG: %s' % m.group('name'))
	                #print ('MSG: %s' % m.group('message'))
	                #retorna data, nome e mensagem, nenhuma acao
	                return (m.group('datetime'), m.group('name'), m.group('message'), None)
	        
	        # if code comes here, message is continuation or action
	        for pattern in map(lambda x:x+SPIWhatsAppEmailsParser.action_pattern, SPIWhatsAppEmailsParser.date_patterns.values()):
	            m = re.search(pattern, str)
	            #se encontrou o padrao da mensagem
	            if m:
	                if any(action_string in m.group('action') for action_string in SPIWhatsAppEmailsParser.action_strings.values()):
	                    for pattern in map(lambda x: "(?P<name>(.*?))"+x+"(.*?)", SPIWhatsAppEmailsParser.action_strings.values()):
	                        m_action = re.search(pattern, m.group('action'))
	                        if m_action:
	                            return (m.group('datetime'), m_action.group('name'), None, m.group('action'))
	                    
	                    print("[erro em capturar a acao - necessario verificar] - %s\n" %(m.group('action')))
	                    return (m.group('datetime'), None, None, m.group('action'))
	        
	        #controle
	        #print ("continuacao ou nao esta no padrao")
	        #prone to return invalid continuation if above filtering doesn't cover all patterns for messages and actions
	        return (None, None, str, None)
	    
	    #processa a mensagem
	    def process(self, content):
	        messages = []
	        #cria objeto vazio - datetime, name, message, action
	        null_chat = SPIWhatsAppEmailsParser.WhatsAppChatElement('', '', '', '')
	        
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
	                messages.append(SPIWhatsAppEmailsParser.WhatsAppChatElement(parsed[0],parsed[1],parsed[2], parsed[3]))			
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
			print (n.group('Numero'), n.group('Name'))
			self.createContact(n.group('Numero'), n.group('Name'))
			arquivos.append(f)  #ok
		
		for f in arquivos:
			#controla os participantes deste chat
			chat_participantes = {}
			
			#usuario sempre eh um participante do chat
			chat_participantes[self.usuario.Name.Value] = self.usuario.Username.Value
			
			#novo objeto chat, estado nao excluido
			chat = Chat()
			chat.Deleted = DeletedState.Intact
			
			#match com nome do arquivo
			rchat_name_parser = re.match(r'/Conversa do WhatsApp com (?P<Name>.*)/CHAT_(?P<Numero>[0-9]*@s\.whatsapp\.net)\.txt', f.AbsolutePath)
			chat.Id.Value = (rchat_name_parser.group('Numero')).split("@")[0][2:]
			chat.Source.Value = "WhatsApp (EmailExport)"
			
			
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
							print ("!!!WARNING!!! Attachment file not found: %s" % anexo_parser.group(1))
					
					#midia nao exportada ou ausente
					anexo_ausente = re.match(r'(<M(.*)dia omitida>)|(<Arquivo de m(.*)dia oculto>)|(<media omitted>)', m.message)
					if not anexo_ausente is None: 
						#print ("anexo oculto")
						im.Body.Value = im.Body.Value+" -<O anexo nao foi localizado no dispositivo>"
				else:
					#se eh uma acao	
					im.Body.Value = ("( %s )" % m.action)
				party = Party()
				#se esse remetente nao esta inserido nos participantes ainda, entao insere
				if m.name not in chat_participantes:
				    chat_participantes[m.name] = rchat_name_parser.group('Numero')
				    chat.Participants.Add(party)
				
				party.Identifier.Value = chat_participantes[m.name]
				party.Name.Value = m.name
				#print self.usuario.Name.Value
				if m.name == self.usuario.Name.Value:
				    party.Role.Value = PartyRole.To
				    im.From.Value = party
				    im.Direction = ModelDirections.Outgoing
				    #print("mensagem do usuario")
				else:
				    party.Role.Value = PartyRole.From
				    im.From.Value = party
				    im.Direction = ModelDirections.Incoming
				
				#data da mensagem
				im.TimeStamp.Value = m.datetime
				#o que significa?
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
print ("Starting")
#para indicativo final do script
startTime = time.time()

#calling the parser for results
results = SPIWhatsAppEmailsParser().parse()
ds.Models.AddRange(results)
print ("Finished - The script took %s seconds !" % format(time.time() - startTime))


