from telegram.ext import Updater, CommandHandler, MessageHandler, InlineQueryHandler, Filters
from telegram import InlineQueryResultArticle, InputTextMessageContent, ParseMode
import os
import logging
import signal
import sys
import time
import threading
import requests
import calendar
from time import sleep

## Constants
DAYS = list(calendar.day_name)

def start(bot, update):
	help_string = \
		"""Hello, I am the unofficial Hiking Buddies Munich Bot.
		I can help you look up events by organiser, date, difficulty etc.
		Commands:
			1. /allevents : List all events
			2. /eventsweek: List all events in the current week (including coming Sunday)
			3. /eventsweek <difficulty>: List all events for current week with difficulty > <difficulty>
					eg: /eventsweek T4
			4. /eventsweek <difficultyLower> <difficultyUpper>: List all events for current week by difficulty (T1-T6)
					eg: /eventsDate
			5. /eventsorganiser <organiser name>: List all events by organiser
					eg: /eventsorganiser Suhaib
			5. /eventsdate <startDate> <endDate>: List all events within specified date"""
	bot.send_message(chat_id=update.message.chat_id, text=help_string)


def echo(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=update.message.text)

def caps(bot, update, args):
    text_caps = ' '.join(args).upper()
    bot.send_message(chat_id=update.message.chat_id, text=text_caps)


def makerequest():
	url = 'https://www.hiking-buddies.com/routes/event_list/get_event_list/'
	params = dict(
		[
			('draw', 5),
			('columns[0][data]', 0),
			('columns[0][name]', ''),
			('columns[0][searchable]', False),
			('columns[0][orderable]', False),
			('columns[0][search][value]', ''),
			('columns[0][search][regex]', False),
			('columns[1][data]', 1),
			('columns[1][name]', ''),
			('columns[1][searchable]', True),
			('columns[1][orderable]', True),
			('columns[1][search][value]', ''),
			('columns[1][search][regex]', False),
			('columns[2][data]', 2),
			('columns[2][name]', ''),
			('columns[2][searchable]', False),
			('columns[2][orderable]', True),
			('columns[2][search][value]', ''),
			('columns[2][search][regex]', True),
			('columns[3][data]', 3),
			('columns[3][name]', ''),
			('columns[3][searchable]', False),
			('columns[3][orderable]', True),
			('columns[3][search][value]', ''),
			('columns[3][search][regex]', False),
			('columns[4][data]', 4),
			('columns[4][name]', ''),
			('columns[4][searchable]', False),
			('columns[4][orderable]', True),
			('columns[4][search][value]', ''),
			('columns[4][search][regex]', False),			
			('columns[5][data]', 5),
			('columns[5][name]', ''),
			('columns[5][searchable]', False),
			('columns[5][orderable]', True),
			('columns[5][search][value]', ''),
			('columns[5][search][regex]', False),
			('start', 0),
			('length', 100),
			('search[value]', ''),
			('search[regex]', False),
			('id', 'id_future')
		]
	)
	resp = requests.get(url=url, params=params)
	logging.info(resp.url)
	logging.info(resp.status_code)
	try:
		return resp.json()
	except Exception as error:
		logging.error(resp.text)
		return "Sorry! Sometimes even bots are useless. I will ask my master for a fix."


def get_date_string(web_date):
	date_arr = web_date.split(',')
	## TODO: Add verification of input
	weekday = int(date_arr[0])
	day = date_arr[1]
	month = date_arr[2]
	# year = int(date_arr[3])
	hour = date_arr[4]
	minute = date_arr[5]
	return "%.3s, %2s.%2s, %2s:%2s" % (DAYS[weekday-1], day, month, hour, minute)


def all_events(bot, update):
	logging.info("handling all events")
	hikes = makerequest()['data']
	# Begin response text
	response = ""
	for hike in hikes:
		event_link = 'https://www.hiking-buddies.com/routes/events/%s/' % (hike[5])
		response +=  "*%4s.*  [%25s](%s)  %3s  __%15s__  %15s\n" % \
			(hike[5], hike[1].replace('[', '<').replace(']', '>'), event_link, hike[2], hike[3], get_date_string(hike[4]))
	# End response text
	bot.send_message(
		parse_mode = ParseMode.MARKDOWN,
		chat_id=update.message.chat_id, 
		text=response,
		disable_web_page_preview = True
	)


def inline(bot, update):
    query = update.inline_query.query
    if not query:
        return
    query
    results = list()
    results.append(
        InlineQueryResultArticle(
            id=query.upper(),
            title='Caps',
            input_message_content=InputTextMessageContent("Sorry this feature is still pending")
        )
    )
    bot.answer_inline_query(update.inline_query.id, results)

if __name__ == "__main__":
	# For security read token from environment variable
	updater = Updater(token=os.environ['TELEGRAM_TOKEN'])
	dispatcher = updater.dispatcher

	# Setup logging
	logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
	                     level=logging.INFO)

	# Define handlers
	start_handler = CommandHandler('start', start)
	help_handler = CommandHandler('help', start)
	allevents_handler = CommandHandler('allevents', all_events)
	echo_handler = MessageHandler(Filters.text, echo)
	caps_handler = CommandHandler('caps', caps, pass_args=True)
	inline_command_handler = InlineQueryHandler(inline)
	
	# Add handlers to dispatcher
	dispatcher.add_handler(start_handler)
	dispatcher.add_handler(help_handler)
	dispatcher.add_handler(allevents_handler)
	dispatcher.add_handler(inline_command_handler)

	# Start polling
	updater.start_polling()

	# For ending app
	def signal_handler(signal, frame):
	    print('Terminating program...')
	    # Stop updater before exiting
	    updater.stop()
	    print('Done!')
	    sys.exit(0)
	signal.signal(signal.SIGINT, signal_handler)
	forever = threading.Event()
	forever.wait()
