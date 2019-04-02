from pymessenger.bot import Bot


"""
This bot listens to port 80 for incoming connections from Facebook. It takes
in any messages that the bot receives and echos it back.
"""
from flask import Flask, request
from pymessenger.bot import Bot

app = Flask(__name__)

ACCESS_TOKEN = ""
VERIFY_TOKEN = ""
bot = None


@app.route("/", methods=['GET', 'POST'])
def hello():
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        else:
            return 'Invalid verification token'

    if request.method == 'POST':
        output = request.get_json()
        for event in output['entry']:
            messaging = event['messaging']
            for x in messaging:
                if x.get('message'):
                    recipient_id = x['sender']['id']
                    if x['message'].get('text'):
                        message = x['message']['text']
                        bot.send_text_message(recipient_id, message)
                    if x['message'].get('attachments'):
                        for att in x['message'].get('attachments'):
                            bot.send_attachment_url(recipient_id, att['type'], att['payload']['url'])
                else:
                    pass
        return "Success"


if __name__ == "__main__":
	# Setup logging
    logging.basicConfig(format='HBMMessengerBot %(asctime)s - %(name)s - %(levelname)s - %(message)s',
                         level=logging.INFO)
    # For security read token from environment variable
    if "MESSENGER_ACCESS_TOKEN" not in os.environ:
        logging.error("Please set MESSENGER_ACCESS_TOKEN in the environment")
        sys.exit(0)
    if "MESSENGER_VERIFY_TOKEN" not in os.environ:
        logging.error("Please set MESSENGER_VERIFY_TOKEN in the environment")
        sys.exit(0)
    ACCESS_TOKEN = os.environ['MESSENGER_ACCESS_TOKEN']
    VERIFY_TOKEN = os.environ['MESSENGER_VERIFY_TOKEN']
    bot = Bot(ACCESS_TOKEN)
    app.run(port=80, debug=True)