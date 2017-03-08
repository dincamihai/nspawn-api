import sys
import re
import uuid
import shlex
import json
import logging
from pydbus import SystemBus
from logging.handlers import RotatingFileHandler
from subprocess import Popen, PIPE
from threading import Thread, Event
from Queue import Queue, Empty
from flask import Flask, request, jsonify, Response, abort
from pydbus import SystemBus


logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s')


def create_app():
    app = Flask(__name__)
    app.config['DEBUG'] = True

    app.bus = SystemBus()
    app.machined = app.bus.get('.machine1')

    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    app.logger.addHandler(handler)
    # handler = RotatingFileHandler('nspawn-api.log', maxBytes=10000, backupCount=1)
    # handler.setLevel(logging.DEBUG)
    # app.logger.addHandler(handler)

    return app


app = create_app()


@app.route("/start", methods=['POST'])
def start():
    start_proc = _start(request.values['machine'])
    return jsonify({'success': start_proc.returncode == 0})


@app.route("/clone", methods=['POST'])
def clone():
    cloneid = request.values.get('target', uuid.uuid4())
    try:
        app.machined.CloneImage(request.values['machine'], cloneid, False)
    except:
        return jsonify({'success': False})
    return jsonify({'success': True, 'containerid': cloneid})


@app.route("/stop", methods=['POST'])
def stop():
    proc = _poweroff(request.values['machine'])
    return jsonify({'success': proc.returncode == 0})


@app.route("/remove", methods=['DELETE'])
def remove():
    remove_proc = _remove(request.values['machine'])
    return jsonify({'success': remove_proc.returncode == 0})


@app.route("/bind", methods=['POST'])
def bind():
    bind_proc = _bind(
        request.values['machine'],
        request.values['source_path'],
        request.values['target_path'],
        request.values['mode'])
    return jsonify({'success': bind_proc.returncode == 0})


@app.route("/inspect", methods=['POST'])
def inspect():
    pid = _get_machine_pid(request.values['machine'])
    nsenter_proc = _nsenter(pid, "ip mon addr")

    queue = Queue()
    thread = Thread(target=enqueue_output, args=(nsenter_proc.stdout, queue))
    thread.start()
    ip = ''
    while True:
        try:
            line = queue.get_nowait()
        except Empty:
            continue
        if line.startswith('2: mv-em1    inet '):
            match = re.search("inet (?P<ip>[0-9.]*)", line)
            if match:
                ip = match.groupdict()['ip']
                nsenter_proc.terminate()
                break

    return jsonify({'NetworkSettings': {'IPAddress': ip}})


@app.route("/run", methods=['POST'])
def run():
    pid = _get_machine_pid(request.values['machine'])
    app.logger.info("Running: {0}".format(request.values))
    nsenter_proc = _nsenter(pid, request.values['command'])
    if request.values.get('stream') == 'False':
        (stdoutdata, stderrdata) = nsenter_proc.communicate()
        return jsonify(dict(stdoutdata=stdoutdata, stderrdata=stderrdata))
    else:
        queue = Queue()
        thread = Thread(
            target=enqueue_output, args=(nsenter_proc.stdout, queue))
        thread.start()

        def read():
            while True:
                try:
                    yield queue.get_nowait()
                except Empty:
                    continue

        return Response(read(), mimetype='text/plain')


@app.route("/copy-to", methods=['POST'])
def copyto():
    app.logger.info("Copying: {0}".format(request.values))
    try:
        app.machined.CopyToMachine(
            request.values['machine'],
            request.values['source'],
            request.values['target'])
    except Exception as ex:
        abort(500)
    return jsonify({'success': True})


def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()


def _nsenter(pid, command):
    pattern = "nsenter --target {0} --mount --uts --ipc --net --pid -- {1}"
    proc = Popen(
        shlex.split(pattern.format(pid, command)),
        stdout=PIPE, stderr=PIPE)
    return proc


def _get_machine_pid(name):
    return app.bus.get('.machine1', app.machined.GetMachine(name)).Leader


def _start(machine):
    return _run("machinectl start {0}".format(machine))


def _poweroff(machine):
    return _run("machinectl poweroff {0}".format(machine))


def _remove(machine):
    return _run("machinectl remove {0}".format(machine))


def _bind(machine, source_path, target_path, mode):
    return _run("machinectl --mkdir bind {0} {1} {2} {3}".format(
        '--read-only' if mode == 'ro' else '',
        machine, source_path, target_path))


def _run(cmd):
    app.logger.info("Running: {0}".format(cmd))
    ON_POSIX = 'posix' in sys.builtin_module_names
    proc = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE)
    (stdoutdata, stderrdata) = proc.communicate()
    if stdoutdata:
        app.logger.info(stdoutdata)
    if stderrdata:
        app.logger.error(stderrdata)
    return proc


if __name__ == "__main__":
    app.run()
