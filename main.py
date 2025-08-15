




import time
import random
import yaml
from utils.linkedin_bot import LinkedInBot

def load_accounts(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)['accounts']

if __name__ == "__main__":
    accounts = load_accounts("credentials/accounts.yaml")
    for acc in accounts:
        print(f"\n🔐 Processing Account: {acc['username']}")
        bot = LinkedInBot(acc['username'], acc['password'])
        bot.run()
        time.sleep(random.uniform(10, 20))
