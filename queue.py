import types
import Queue
import threading
import logging
from influxdb import client as influxdb


class QueueMachine:
    def __init__(self, name, num_workers, worker, influxserver):
        if type(num_workers) != int:
            raise TypeError
        if num_workers < 1:
            raise ValueError
        if not isinstance(worker, types.FunctionType):
            raise TypeError

        self.name = name
        self.q = Queue.Queue()
        for i in range(num_workers):
            t = threading.Thread(target=worker, args=(self.q,))
            t.daemon = True
            t.start()
        if influxserver:
            self.influxdb = influxdb.InfluxDBClient(database="motech")
            self.log_db(-1)

        self.log_stats(-1)
        logging.debug("Created {}-queue, {} thread{}".format(name, num_workers, "s" if num_workers > 1 else ""))

    def put(self, payload):
        logging.debug("Added {} to the '{}' queue".format(payload, self.name))
        self.q.put(payload)

    def stats(self):
        return "{}-queue: {}".format(self.name, self.q.qsize())

    def log_db(self, last_size):
        size = self.q.qsize()
        if last_size != size:
            self.influxdb.write_points([{
                    "name": self.name,
                    "columns": ["value"],
                    "points": [[size]],
                }])
        threading.Timer(1.0, self.log_db, (size,)).start()

    def log_stats(self, last_message):
        message = self.stats()
        if message != last_message:
            logging.info(message)
        threading.Timer(1.0, self.log_stats, (message,)).start()
