# Hiking Buddies Telegram Bot
Telegram bot for [Hiking Buddies Munich](https://hiking-buddies.com)

Add it to telegram here: https://telegram.me/HikingBuddiesBot

Current functionality is listed below:
1. `/eventsall` : List all events
2. `/eventsweek`: List all events in the current week (including coming Sunday)
3. `/eventsweek <difficulty>`: List all events for current week with difficulty great than <difficulty>  
  eg: `/eventsweek T4`
4. `/eventsweek <difficultyLower> <difficultyUpper>`: List all events for current week by difficulty (T0-T6)  
        eg: `/eventsweek T1 T3`
5. `/eventsorganiser <organiser name>`: List all events by organiser  
  eg: `/eventsorganiser Suhaib`
6. `/eventsdate <startDate> <endDate>`: List all events within specified date | Unimplemented
7. `/subscribe <subscription name> <command> <command args>`: Subscribe to a command from 1-5. Get a notification everytime a new hike appears for that command.  
  eg: `/subscribe hikes_above_t4 eventsweek T4`
8. `/subscribe list`: List current subscriptions
9. `/subscribe remove <subscription name>`: Remove subscription name


## Developer Guide
To run locally you need a TELEGRAM_TOKEN. See https://core.telegram.org/bots

Requires `virtualenv` and `pip`

```
python -m virtualenv myenv
source myenv/bin/activate
pip install -r requirements.txt
export TELEGRAM_TOKEN=<my_token>; python bot.py
```
