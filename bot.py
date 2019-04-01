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
from datetime import datetime, timedelta
from threading import Thread
import sqlite3
from queue import Queue
import queue
import json
from enum import Enum

## Enums
class Difficulty(Enum):
    T0 = 0
    T1 = 1
    T2 = 2
    T3 = 3
    T4 = 4
    T5 = 5
    T6 = 6

## Constants
DAYS = list(calendar.day_name)
PUBLIC_ENUMS = {
    'Difficulty': Difficulty
}

## Global shared variables
__hikes_data__ = []
__latest_hike_id__ = 0
__subscription_queue__ = Queue()
__subscriptions__ = dict()


## Class Definitions

class EnumEncoder(json.JSONEncoder):
    def default(self, obj):
        if type(obj) in PUBLIC_ENUMS.values():
            return {"__enum__": str(obj)}
        return json.JSONEncoder.default(self, obj)


class Job(threading.Thread):
    
    #
    # task_callback is the task to be executed by the job
    # sleep_seconds the number of seconds to sleep before executing the task again
    def __init__(self, sleep_seconds):
        threading.Thread.__init__(self)
        
        # The shutdown_flag is a threading.Event object that
        # indicates whether the thread should be terminated.
        self.shutdown_flag = threading.Event()
        self.sleep_seconds = sleep_seconds
 
    def run(self):
        logging.info('Thread #%s started' % self.ident)
        
        # Thread initialization code
        self.setup()

        while not self.shutdown_flag.is_set():
            self.task()
            time.sleep(self.sleep_seconds)
 
        # Thread cleanup code
        self.cleanup()
        print('Thread #%s stopped' % self.ident)

    def setup(self):
        pass

    def task(self):
        pass

    def cleanup(self):
        pass


class SubscriptionHandler(Job):

    def setup(self):
        global __subscriptions__
        self.conn = sqlite3.connect('hbm.db')
        c = self.conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS subscriptions (id TEXT PRIMARY KEY, " \
            "chat_id INT, name TEXT, command TEXT, last_id INT)")
        self.conn.commit()
        c.execute("SELECT * FROM subscriptions")
        results = c.fetchall()
        subs = dict()
        for result in results:
            subs[result[0]] = {
                'id': result[0],
                'chat_id': result[1],
                'name': result[2],
                'command': json.loads(result[3], object_hook = as_enum),
                'last_id': result[4]
            }
        __subscriptions__ = subs

    def task(self):
        global __subscriptions__
        logging.info("running task")
        again = True
        c = self.conn.cursor()
        while again:
            try:
                subscription = __subscription_queue__.get(block = False)
                action = subscription.pop('action', None)
                if action == 'add':
                    c.execute("REPLACE INTO subscriptions VALUES (?, ?, ?, ?, ?)", 
                        (subscription['id'], subscription['chat_id'], subscription['name'], 
                            json.dumps(subscription['command'], cls = EnumEncoder), subscription['last_id']))
                    __subscriptions__[subscription['id']] = subscription
                elif action == 'remove':
                    c.execute("DELETE FROM subscriptions WHERE name = ? AND chat_id = ?",
                        (subscription['name'], subscription['chat_id']))
                    __subscriptions__.pop(subscription['id'], None)
                else:
                    log.error("Unknown action while pulling from subscription queue: %s" % action)
                # Keep emptying until nothing is found
                again = True
            except queue.Empty as e:
                again = False
                pass
        self.conn.commit()
        logging.info("task completed")

    def cleanup(self):
        self.task()
        self.conn.close()


class HikesLoader(Job):
    def task(self):
        global __latest_hike_id__
        global __hikes_data__
        response = makerequest()
        result = []
        if response is not None:
            hikes = response['data']
            for hike in hikes:
                hike_id = int(hike[5])
                __latest_hike_id__ = hike_id if __latest_hike_id__ < hike_id else __latest_hike_id__
                result.append(
                    { 'id': int(hike[5]),
                      'name': hike[1],
                      'difficulty': Difficulty[hike[2]] if hike[2] in Difficulty.__members__ else Difficulty.T0,
                      'organiser': hike[3],
                      'date': parse_date_string(hike[4]),
                      'link': 'https://www.hiking-buddies.com/routes/events/%s/' % (hike[5])
                    }
                )
        ## put the result in the global variable
        __hikes_data__ = result

## End Class Definitions


## Begin Helper Functions
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
        return None


def command_to_str(command):
    if command['valid']:
        if command['command'] == "eventsall":
            return "eventsall"
        elif command['command'] == "eventsweek":
            return "eventsweek %s %s" % (command['diff_lo'], command['diff_hi'])
        elif command['command'] == "eventsorganiser":
            return "eventsorganiser %s" % command['organiser']
        else:
            return "invalid command"
    else:
        return "[cannot print command!]"


def as_enum(d):
    if "__enum__" in d:
        name, member = d["__enum__"].split(".")
        return getattr(PUBLIC_ENUMS[name], member)
    else:
        return d


# Get next weekday date where weekday is 0 for Monday, 1 for Tuesday... 6 for Sunday
def next_weekday(d, weekday):
    days_ahead = weekday - d.weekday()
    # Target day already happened this week
    if days_ahead <= 0:
        days_ahead += 7
    return d + timedelta(days_ahead)


def get_date_string(hike_dt):
    return "%.3s, %02d.%02d, %02d:%02d" % \
        (DAYS[hike_dt.weekday()], hike_dt.day, hike_dt.month, hike_dt.hour, hike_dt.minute)


def parse_date_string(web_date):
    date_arr = web_date.split(',')
    ## TODO: Add verification of input
    # weekday = int(date_arr[0])
    day = int(date_arr[1])
    month = int(date_arr[2])
    year = int(date_arr[3])
    hour = int(date_arr[4])
    minute = int(date_arr[5])
    return datetime(year, month, day, hour, minute)


def is_valid_difficulty(lo, hi, actual):
    if lo is None:
        # set to lowest
        lo = Difficulty.T1
    if hi is None:
        # set to highest
        hi = Difficulty.T6
    return (actual.value >= lo.value) and (actual.value <= hi.value)


def send_message(bot, chat_id, hikes, response = ""):
    for hike in hikes:
        response +=  "*%4s.*  [%25s](%s)  %3s  __%15s__  %15s\n" % \
            (hike['id'], hike['name'].replace('[', '<').replace(']', '>'), 
                hike['link'], hike['difficulty'].name, hike['organiser'], get_date_string(hike['date']))
    if len(response) > 0:
        bot.send_message(
            parse_mode = ParseMode.MARKDOWN,
            chat_id = chat_id,
            text = response,
            disable_web_page_preview = True
        )
    else:
        bot.send_message(
            chat_id = chat_id,
            text = "No matching hikes found!"
        )


def get_eventsall():
    return __hikes_data__


def get_eventsweek(diff_low, diff_hi):
    today = datetime.now()
    next_monday = next_weekday(today, 0)
    return [ hike for hike in __hikes_data__
        if hike['date'] < next_monday and is_valid_difficulty(diff_low, diff_hi, hike['difficulty']) ]


def get_eventsorganiser(name):
    return [ hike for hike in __hikes_data__ if name.lower() in hike['organiser'].lower() ]


def parse_command(command, args):
    result = dict()
    if command == "eventsall":
        result = {
            'valid': True,
            'command': 'eventsall'
        }
    elif command == 'eventsweek':
        diff_result = parse_difficulty(args)
        if diff_result['valid']:
            diff_result['command'] = 'eventsweek'
            result = diff_result
    elif command == "eventsorganiser":
        if len(args) > 0:
            result = {
                'valid': True,
                'command': 'eventsorganiser',
                'organiser': ' '.join(args)
            }
        else:
            result = { 'valid': False, 'reason': 'organiser must be present' }
    else:
        result = { 'valid': False, 'reason': 'Unknown command ' + command }
    return result


def parse_subscription_command(args):
    result = { 'valid': True }
    if len(args) > 0 and "list" == args[0]:
        result['command'] = "list"
    elif len(args) > 1:
        subscription_name = args[0]
        command = args[1]
        command_args = args[2:]
        if command == "remove":
            if len(args) > 0:
                result['command'] = 'remove'
                result['subscription_name'] = args[0]
            else:
                result = { 'valid': False, 'reason': "Usage: /subscribe <subscription name> remove" }
        else:
            result = parse_command(command, args)
            result['subscription_name'] = subscription_name
    else:
        result = { 'valid': False, 'reason': "Usage: /subscribe <subscription name> <command> <command args>" }
    return result


def parse_difficulty(args):
    result = { 'valid': True, 'diff_lo': Difficulty.T1, 'diff_hi': Difficulty.T6 }
    if len(args) > 0:
        if args[0] in Difficulty.__members__:
            result['diff_lo'] = Difficulty[args[0]]
        else:
            result = {'valid': False, 'reason': 'Difficulty must be of the format T<n> where n is a number between 0-6'}
    if len(args) > 1 and result['valid']:
        if args[1] in Difficulty.__members__:
            diff_hi = Difficulty[args[1]]
        else:
            result = {'valid': False, 'reason': 'Difficulty must be of the format T<n> where n is a number between 0-6'}
    return result


def execute_command(command):
    if command['valid']:
        if command['command'] == "eventsall":
            return { 'result': get_eventsall(), 'valid': True }
        elif command['command'] == "eventsweek":
            return { 'result': get_eventsweek(command['diff_lo'], command['diff_hi']), 'valid': True }
        elif command['command'] == "eventsorganiser":
            return { 'result': get_eventsorganiser(command['organiser']), 'valid': True }
        else:
            return {'valid': False, 'reason': 'unknown command'}
    else:
        # If invalid the command has the reason for not being okay
        return command


## End Helper functions

## Begin command functions
def start(bot, update):
    help_string = \
        """Hello, I am the unofficial Hiking Buddies Munich Bot.
        I can help you look up events by organiser, date, difficulty etc.
        Commands:
            1. /eventsall : List all events
            2. /eventsweek: List all events in the current week (including coming Sunday)
            3. /eventsweek <difficulty>: List all events for current week with difficulty great than <difficulty>
                    eg: /eventsweek T4
            4. /eventsweek <difficultyLower> <difficultyUpper>: List all events for current week by difficulty (T0-T6)
                    eg: /eventsDate
            5. /eventsorganiser <organiser name>: List all events by organiser
                    eg: /eventsorganiser Amit
            6. /eventsdate <startDate> <endDate>: List all events within specified date | Unimplemented
            7. /subscribe <subscription name> <command> <command args>: Subscribe to a command from 1-5. Get a 
                    notification everytime a new hike appears for that command. 
                    eg: /subscribe hikes_above_t4 eventsweek T4
            8. /subscribe list: List current subscriptions
            9. /subscribe remove <subscription name>: Remove subscription name"""
    bot.send_message(chat_id=update.message.chat_id, text=help_string)


def eventsall(bot, update):
    logging.info("handling all events")
    send_message(bot, update.message.chat_id, get_eventsall())


def eventsweek(bot, update, args):
    logging.info("handling eventsweek")
    diff_result = parse_difficulty(args)
    if diff_result['valid']:
        send_message(bot, update.message.chat_id, get_eventsweek(diff_result['diff_lo'], diff_result['diff_hi']))
    else:
        bot.send_message(chat_id = update.message.chat_id, text = diff_result['reason'])


def eventsorganiser(bot, update, args):
    logging.info("handling eventsorganiser")
    hikes = makerequest()['data']
    if len(args) > 0:
        name = ' '.join(args)
        send_message(bot, update.message.chat_id, get_eventsorganiser(name))
    else:
        bot.send_message(chat_id = update.message.chat_id, text = "Please specify the organiser name.")


def subscribe(bot, update, args):
    logging.info("handling subscription")
    parsed_command = parse_subscription_command(args)
    response = ""
    if parsed_command['valid']:
        if parsed_command['command'] == "list":
            for subscription in __subscriptions__.values():
                response += "%10s  %s\n" % (subscription['name'], command_to_str(subscription['command']))
            if response == "":
                response = "No subscriptions found"
        elif parsed_command['command'] == "remove":
            __subscription_queue__.put({
                    'action': 'remove',
                    'id': str(update.message.chat_id) + "_" + parsed_command['subscription_name'],
                    'name': parsed_command['subscription_name'],
                    'chat_id': update.message.chat_id
                })
            response = "%s subscription removed" % parsed_command['subscription_name']
        else: # Else this is a normal command. Add it to queue 
            subscription_name = parsed_command.pop('subscription_name')
            __subscription_queue__.put({
                    'action': 'add',
                    'id': str(update.message.chat_id) + "_" + subscription_name,
                    'chat_id': update.message.chat_id,
                    'name': subscription_name,
                    'command': parsed_command,
                    'last_id': __latest_hike_id__
                })
            response = "%s subscription added" % subscription_name
    else:
        response = parsed_command['reason']
    bot.send_message(chat_id = update.message.chat_id, text = response)


def send_subscriptions(bot, job):
    logging.info("sending subscriptions")
    # We will execute commands only once
    eventsall = None
    eventsweek = dict()
    eventsorganiser = dict()
    # This is bad for now. If we have a lot of subscriptions we can start caching results
    for subscription in __subscriptions__.values():
        result = execute_command(subscription['command'])
        # We ignore invalid results
        if result['valid']:
            hikes = [hike for hike in result['result'] if hike['id'] > subscription['last_id']]
            # Only send if we found some hike
            if len(hikes) > 0:
                send_message(bot, subscription['chat_id'], hikes, 
                    response = "*Subscription: %s*\n" % subscription['name'])
            __subscription_queue__.put({
                    'action': 'add',
                    'id': subscription['id'],
                    'chat_id': subscription['chat_id'],
                    'name': subscription['name'],
                    'command': subscription['command'],
                    'last_id': __latest_hike_id__
                })
    

def inline(bot, update):
    query = update.inline_query.query
    if not query:
        return
    query
    results = list()
    results.append(
        InlineQueryResultArticle(
            id=query.upper(),
            title='Feature pending',
            input_message_content=InputTextMessageContent("Sorry this feature is still pending")
        )
    )
    bot.answer_inline_query(update.inline_query.id, results)
## End command functions


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                         level=logging.INFO)
    # For security read token from environment variable
    if "TELEGRAM_TOKEN" not in os.environ:
        logging.error("Please set TELEGRAM_TOKEN in the environment")
        sys.exit(0)

    updater = Updater(token=os.environ['TELEGRAM_TOKEN'])
    dispatcher = updater.dispatcher
    job_queue = updater.job_queue

    # Jobs
    j1 = SubscriptionHandler(10)
    j2 = HikesLoader(30)
    j1.start()
    j2.start()

    # Define handlers
    start_handler = CommandHandler('start', start)
    help_handler = CommandHandler('help', start)
    allevents_handler = CommandHandler('eventsall', eventsall)
    eventsweek_handler = CommandHandler('eventsweek', eventsweek, pass_args = True)
    eventsorganiser_handler = CommandHandler('eventsorganiser', eventsorganiser, pass_args = True)
    subscribe_handler = CommandHandler('subscribe', subscribe, pass_args = True)
    inline_command_handler = InlineQueryHandler(inline)
    
    # Add handlers to dispatcher
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(allevents_handler)
    dispatcher.add_handler(eventsweek_handler)
    dispatcher.add_handler(eventsorganiser_handler)
    dispatcher.add_handler(subscribe_handler)
    dispatcher.add_handler(inline_command_handler)

    ## Queued jobs
    job_queue.run_repeating(callback = send_subscriptions, interval = 15)

    # Start polling
    updater.start_polling()

    # For ending app
    def signal_handler(signal, frame):
        logging.info('Terminating program...')
        # Stop updater before exiting
        logging.info("Stopping updater")
        updater.stop()
        logging.info("Stopping subscription handler")
        j1.shutdown_flag.set()
        logging.info("Stopping hikes loader")
        j2.shutdown_flag.set()
        j1.join(2)
        j2.join(2)
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    forever = threading.Event()
    forever.wait()
