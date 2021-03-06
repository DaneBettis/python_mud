from Event.Event import Event
from Event.EventHandler import EventHandler
from Event.EventReceiver import EventReceiver
import threading
from lib import ANSI

class Room(EventReceiver):
	def __init__(self):
		EventReceiver.__init__(self)
		attributes = {
			'playerSemaphore'	: threading.BoundedSemaphore(1),
			'npcSemaphore'		: threading.BoundedSemaphore(1),
			'roomID'			: '',
			'name'				: '',
			'description'		: [],
			'exits'				: [],
			'players'			: [],
			'npcs'				: [],
			'spawnableNPCs'		: [],
			'updateRate'		: 0
		}
		
		for key in attributes.keys():
			self.attributes[key] = attributes[key]
		
		
		self.addEventHandler(PlayerEnteredHandler())
		self.addEventHandler(PlayerExitedHandler())
		self.addEventHandler(PlayerLogoutHandler())
		self.addEventHandler(ActorMovedHandler())
		self.addEventHandler(WasObservedHandler())
		self.addEventHandler(ActorObservedHandler())
		self.addEventHandler(ActorEmotedHandler())
		
		
	def removePlayer(self, player):
		playerList = self.attributes['players']

		self.attributes['playerSemaphore'].acquire()

		if player in set(playerList):
			playerList.remove(player)

		self.attributes['playerSemaphore'].release()


	def addPlayer(self, player):
		playerList	= self.attributes['players']

		self.attributes['playerSemaphore'].acquire()

		if player not in set(playerList):			
			playerList.append(player)
			player.attributes['roomID'] = self.attributes['roomID']
			player.insertCommand('look')

		self.attributes['playerSemaphore'].release()
		
		
		
		
		
		
class ActorEmotedHandler(EventHandler):
	def __init__(self):
		EventHandler.__init__(self)
		self.attributes['signature']	= 'actor_emoted'
		self.attributes['function']		= self.actorEmoted

	def actorEmoted(self, receiver, event):
		targetName	= event.attributes['data']['target']
		playerList	= filter(lambda player: 
								player != event.attributes['data']['emoter'],
							receiver.attributes['players'])
		target		= None

		if targetName != None and targetName != '':
			targetList	= filter(lambda player : 
									player.attributes['name'].lower().startswith(targetName.lower()),
									playerList)

			if len(targetList) > 0:
				target = targetList[0]
			else:
				emoter											= event.attributes['data']['emoter']
				feedbackEvent									= Event()
				feedbackEvent.attributes['signature']			= 'received_feedback'
				feedbackEvent.attributes['data']['feedback']	= 'You don\'t see that here.'

				emoter.receiveEvent(feedbackEvent)

				return

		event.attributes['data']['target'] = target	

		for player in receiver.attributes['players']:
			player.receiveEvent(event)





class ActorObservedHandler(EventHandler):
	def __init__(self):
		EventHandler.__init__(self)
		self.attributes['signature']	= 'actor_observed'
		self.attributes['function']		= self.actorObserved


	def actorObserved(self, receiver, event):
		observer	= event.attributes['data']['observer']
		target		= event.attributes['data']['target']
		targetList	= filter(lambda actor : 
								actor.attributes['name'].lower().startswith(target.lower()), 
							receiver.attributes['players'])

		if len(targetList) == 0:
			feedbackEvent									= Event()
			feedbackEvent.attributes['signature']			= 'received_feedback'
			feedbackEvent.attributes['data']['feedback']	= 'You don\'t see that here.'

			observer.receiveEvent(feedbackEvent)
		else:
			lookEvent									= Event()
			lookEvent.attributes['data']['observer']	= observer
			lookEvent.attributes['signature']			= 'was_observed'

			targetList[0].receiveEvent(lookEvent)





class WasObservedHandler(EventHandler):
	def __init__(self):
		EventHandler.__init__(self)
		self.attributes['signature']	= 'was_observed'
		self.attributes['function']		= self.wasObserved


	def wasObserved(self, receiver, event):
		player		= event.attributes['data']['observer']
		description = [ANSI.red(receiver.attributes['name']) + '\n\r']
		exitList	= 'Obvious exits:'
		playerList	= filter(lambda p: p != player, receiver.attributes['players'])

		for line in receiver.attributes['description']:
			description.append(line)

		for exit in receiver.attributes['exits']:
			if exit.attributes['isHidden'] == False:
				exitList = exitList + ' ' + exit.attributes['name'] + ','

		if exitList == 'Obvious exits:':
			exitList = 'Obvious exits: none'

		if exitList.endswith(','):
			exitList = exitList[0:-1]

		description.append(ANSI.blue(exitList))

		if len(playerList) > 0:
			playerLine = 'Players:'

			for p in playerList:
				playerLine = playerLine + ' ' + p.attributes['name'] + ','

			if playerLine.endswith(','):
				playerLine = playerLine[0:-1]

			description.append(ANSI.green(playerLine))

		describeEvent									= Event()
		describeEvent.attributes['signature']			= 'entity_described_self'
		describeEvent.attributes['data']['description'] = description

		player.receiveEvent(describeEvent)





class ActorMovedHandler(EventHandler):
	def __init__(self):
		EventHandler.__init__(self)
		self.attributes['signature']	= 'actor_moved'
		self.attributes['function']		= self.moveActor


	def moveActor(self, receiver, event):
		actor		= event.attributes['data']['source']
		direction	= event.attributes['data']['direction']
		exit		= None

		if direction != None and direction != '':
			exitList = filter(lambda e : 
									e.attributes['name'].lower().startswith(direction.lower()), 
								receiver.attributes['exits'])

			if len(exitList) > 0:
				exit = exitList[0]


		if exit == None:
			feedbackEvent									= Event()
			feedbackEvent.attributes['signature']			= 'received_feedback'
			feedbackEvent.attributes['data']['feedback']	= ANSI.yellow('You can\'t go that way!')

			actor.receiveEvent(feedbackEvent)

		else:			
			currentRoom									= receiver.attributes['roomID']
			destination									= exit.attributes['destination']
			moveEvent									= Event()
			moveEvent.attributes['signature']			= 'move_actor'
			moveEvent.attributes['data']['actor']		= actor
			moveEvent.attributes['data']['fromRoomID']	= currentRoom
			moveEvent.attributes['data']['toRoomID']	= destination
			moveEvent.attributes['data']['exitMessage'] = '{} leaves {}.'.format(actor.attributes['name'], exit.attributes['name'])

			from Engine import RoomEngine
			RoomEngine.receiveEvent(moveEvent)





class PlayerEnteredHandler(EventHandler):
	def __init__(self):
		EventHandler.__init__(self)
		self.attributes['signature']	= 'player_entered'
		self.attributes['function']		= self.playerEntered	


	def playerEntered(self, receiver, event):
		player		= event.attributes['data']['player']
		playerList	= receiver.attributes['players']
		
		if player not in set(playerList):
			receiver.attributes['playerSemaphore'].acquire()
			
			for p in playerList:
				p.receiveEvent(event)
			
			receiver.attributes['playerSemaphore'].release()				
			
			receiver.addPlayer(player)
			
			player.attributes['roomID'] = receiver.attributes['roomID']


		




class PlayerExitedHandler(EventHandler):
	def __init__(self):
		EventHandler.__init__(self)
		self.attributes['signature']	= 'actor_exited'
		self.attributes['function']		= self.playerExited		


	def playerExited(self, receiver, event):
		actor = event.attributes['data']['actor']

		receiver.removePlayer(actor)

		message = event.attributes['data']['exitMessage']

		if message != None and message != '':
			for p in receiver.attributes['players']:
				feedbackEvent									= Event()
				feedbackEvent.attributes['signature']			= 'received_feedback'
				feedbackEvent.attributes['data']['feedback']	= message

				p.receiveEvent(feedbackEvent)





class PlayerLogoutHandler(EventHandler):
	def __init__(self):
		EventHandler.__init__(self)
		self.attributes['signature']	= 'player_logout'
		self.attributes['function']		= self.playerExited		


	def playerExited(self, receiver, event):
		actor = event.attributes['data']['actor']

		receiver.removePlayer(actor)
