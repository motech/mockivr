from flask import Flask, render_template, request
import logging
import call
import queue
import cdr
import time
from contextlib import contextmanager
import argparse


INCOMING_NAME = "incoming"
INCOMING_NUM_THREAD = 30
OUTGOING_NAME = "outgoing"
OUTGOING_NUM_THREAD = 300
CDR_NAME = "cdr"
CDR_NUM_THREAD = 5

TIME_MULTIPLIER = 1.0

now = lambda: int(round(time.time() * 1000))

app = Flask(__name__)


@contextmanager
def timed(action, count=0, object="", objects=""):
    start = now()
    yield
    duration = now() - start
    message = action
    if object and count:
        objs = objects if objects else object + 's'
        if count == 1:
            obj = object
        else:
            obj = objs
        speed = "at "
        if duration == 0:
            speed += "a gazillion {}/sec".format(objs)
        else:
            speed += "{} {}/sec".format(1000 * count / duration, obj)
        message += " {} {} in {}ms {}".format(count, obj, duration, speed)
    else:
        message += " in {}ms".format(duration)

    logging.info(message)


@app.route('/')
def home():
    stats = {
        'cdrs': cdr_machine.stats(),
        'cdr queue': cdr_queue_machine.stats(),
        'incoming queue': incoming_queue_machine.stats(),
        'outgoing queue': outgoing_queue_machine.stats(),
        'incoming calls': incoming_call_machine.stats(),
        'outgoing calls': outgoing_call_machine.stats(),
    }
    return render_template('index.html', stats=stats)


def enqueue_inbound(count):
    with timed('enqueued', count, 'incoming message'):
        for i in range(count):
            #todo randomize
            phone_number = "12065551212"
            incoming_queue_machine.put({'from': phone_number})

    return "{}".format(count)


def is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


@app.route('/out')
def mock_outbound():
    errors = []
    if 'to' not in request.args:
        errors.append("missing 'to' argument")
    if len(errors) > 0:
        return render_template('400.html', errors=errors), 400

    payload = {
        'to': request.args['to'],
    }
    outgoing_queue_machine.put(payload)

    if args.verbose:
        return str(payload)
    else:
        return "OK"


def incoming_queue_worker(q):
    while True:
        payload = q.get()
        logging.debug("Getting payload {} from '{}' queue".format(payload, INCOMING_NAME))
        incoming_call_machine.call(payload)
        q.task_done()


def outgoing_queue_worker(q):
    while True:
        payload = q.get()
        logging.debug("Getting payload {} from '{}' queue".format(payload, OUTGOING_NAME))
        outgoing_call_machine.call(payload)
        q.task_done()


def cdr_queue_worker(q):
    while True:
        payload = q.get()
        logging.debug("Getting payload {} from '{}' queue".format(payload, CDR_NAME))
        cdr_machine.send(payload)
        q.task_done()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--server", help="url of the Motech server",
                        default="http://localhost:8080/motech-platform-server")
    parser.add_argument("-c", "--config", help="name of the ivr config", default="config")
    parser.add_argument("-t", "--template", help="name of the vxml template", default="template")
    parser.add_argument("-n", "--num", help="number of inbound phone calls to mock (must use with -u)", type=int)
    # TODO add more arguments to vary the type of mock inbound call
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    args = parser.parse_args()

    #debug
    #print "args={}".format(args)

    template_url = "{}/module/ivr/template/{}/{}".format(args.server, args.config, args.template)
    cdr_url = "{}/module/ivr/status/{}".format(args.server, args.config)
    if args.verbose:
        print "VXML template URL: {}".format(template_url)
        print "CDR template URL: {}".format(cdr_url)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.WARNING)

    cdr_machine = cdr.CDRMachine()
    cdr_queue_machine = queue.QueueMachine(CDR_NAME, CDR_NUM_THREAD, cdr_queue_worker)

    incoming_call_types = [call.SUCCESS, call.NO_ANSWER, call.PHONE_OFF, call.NOT_DELIVERED]
    incoming_queue_machine = queue.QueueMachine(INCOMING_NAME, INCOMING_NUM_THREAD, incoming_queue_worker)
    incoming_call_machine = call.CallMachine(INCOMING_NAME, cdr_url, template_url, TIME_MULTIPLIER, incoming_call_types,
                                             cdr_queue_machine)

    outgoing_call_types = [call.SUCCESS, call.NO_ANSWER, call.PHONE_OFF, call.NOT_DELIVERED]
    outgoing_queue_machine = queue.QueueMachine(OUTGOING_NAME, OUTGOING_NUM_THREAD, outgoing_queue_worker)
    outgoing_call_machine = call.CallMachine(OUTGOING_NAME, cdr_url, template_url, TIME_MULTIPLIER, outgoing_call_types,
                                             cdr_queue_machine)

    if args.num:
        enqueue_inbound(args.num)

    app.run()
