import logging
import publish

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)

publish.publish("halux/test/activity/activate", "inactive")