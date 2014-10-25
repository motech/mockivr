import threading
import random
import time
import logging


class CallType:
    def __init__(self, name, likelihood, min_duration, max_duration):
        self.name = name
        self.likelihood = likelihood
        self.min_duration = min_duration
        self.max_duration = max_duration

    def random_call_duration(self):
        return random.randrange(self.min_duration, self.max_duration)

SUCCESS = CallType("success", 40, 100*1000, 140*1000)
NO_ANSWER = CallType("no answer", 30, 10*1000, 30*1000)
PHONE_OFF = CallType("phone off", 15, 1000/2, 2*1000)
NOT_DELIVERED = CallType("not delivered", 15, 1000/2, 1*1000)

class CallMachine:

    def __init__(self, name, time_multiplier, types, cdr_queue_machine):
        self.name = name
        self.time_multiplier = time_multiplier
        self.lock = threading.Lock()
        self.types = types
        self.cdr_queue_machine = cdr_queue_machine
        self.likelihoods = []
        self.counts = []

        sum_of_likelihoods = 0
        for i in range(len(types)):
            self.counts.append(0)
            sum_of_likelihoods += types[i].likelihood
            for j in range(types[i].likelihood):
                self.likelihoods.append(i)
        if sum_of_likelihoods != 100:
            raise ValueError("The sum of all likelihoods should be 100 but is {}".format(sum_of_likelihoods))

        self.log_stats("")
        logging.debug("Created '{}' call machine".format(name))

    def call(self):
        i = random.choice(self.likelihoods)
        call_type = self.types[i]
        call_duration = call_type.random_call_duration()
        self.lock.acquire()
        call_count = self.counts[i] + 1
        self.counts[i] = call_count
        self.lock.release()
        time.sleep(call_duration / 1000.0 / self.time_multiplier)
        cdr = "{}-{}".format(call_type.name, call_count)
        logging.debug("The '{}' call machine made the following call: {}".format(self.name, cdr))
        self.cdr_queue_machine.put(cdr)

    def stats(self):
        message = "{}-call: ".format(self.name)

        total = 0
        for i in range(len(self.types)):
            total += self.counts[i]
        message += "{}".format(total)

        if total > 0:
            for i in range(len(self.types)):
                message += ", {0}({1:.2f}%)".format(self.types[i].name, 100.0 * self.counts[i] / total)

        return message

    def log_stats(self, last_message):
        message = self.stats()
        if message != last_message:
            logging.info(message)
        threading.Timer(1.0, self.log_stats, (message,)).start()
