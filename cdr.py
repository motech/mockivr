import threading
import random
import time
import logging


class CDRMachine:

    def __init__(self):
        self.count = 0
        self.lock = threading.Lock()

        self.log_stats("")
        logging.debug("Created the call detail record machine")

    def send(self, cdr):
        self.lock.acquire()
        cdr_id = self.count + 1
        self.count = cdr_id
        self.lock.release()
        logging.debug("Sending cdr id {}: {}".format(cdr_id, cdr))
        #TODO call motech to create a CDR

    def stats(self):
        self.lock.acquire()
        message = "cdr: {}".format(self.count)
        self.lock.release()

        return message

    def log_stats(self, last_message):
        message = self.stats()
        if message != last_message:
            logging.info(message)
        threading.Timer(1.0, self.log_stats, (message,)).start()
