import threading
import Queue
import xbmc
import util


class Task:
    def __init__(self):
        self._canceled = False

    def start(self):
        BGThreader.addTask(self)

    def run(self):
        pass

    def cancel(self):
        self._canceled = True

    def isCanceled(self):
        return self._canceled or xbmc.abortRequested


class BackgroundThreader:
    def __init__(self, name=None):
        self.name = name
        self._queue = Queue.LifoQueue()
        self._thread = None
        self._abort = False
        self._task = None

    def _runTask(self, task):
        if task._canceled:
            return
        try:
            task.run()
        except:
            util.ERROR()

    def abort(self):
        self._abort = True
        return self

    def aborted(self):
        return self._abort or xbmc.abortRequested

    def start(self):
        self._thread = threading.Thread(target=self._queueLoop, name='BACKGROUND-WORKER({0})'.format(self.name))
        self._thread.start()

    def _queueLoop(self):
        util.DEBUG_LOG('BGThreader: queue: Active')
        try:
            while not self.aborted():
                self._task = self._queue.get_nowait()
                self._runTask(self._task)
                self._queue.task_done()
                self._task = None
        except Queue.Empty:
            util.DEBUG_LOG('BGThreader: queue ({0}): Empty'.format(self.name))

        self._queue = Queue.LifoQueue()

        util.DEBUG_LOG('BGThreader: queue ({0}): Finished'.format(self.name))

    def shutdown(self):
        self.abort()

        if self._task:
            self._task.cancel()

        if self._thread and self._thread.isAlive():
            util.DEBUG_LOG('BGThreader: thread ({0}): Waiting...'.format(self.name))
            self._thread.join()
            util.DEBUG_LOG('BGThreader: thread ({0}): Done'.format(self.name))

    def addTask(self, task):
        self._queue.put(task)

        if not self._thread or not self._thread.isAlive():
            self.start()

    def addTasks(self, tasks):
        for t in reversed(tasks):
            self._queue.put(t)

        if not self._thread or not self._thread.isAlive():
            self.start()

    def working(self):
        return not self._queue.empty()


class ThreaderManager:
    def __init__(self):
        self.index = 0
        self.abandoned = []
        self.threader = BackgroundThreader(str(self.index))

    def __getattr__(self, name):
        return getattr(self.threader, name)

    def reset(self):
        if self.threader._queue.empty() and not self.threader._task:
            return

        self.index += 1
        self.abandoned.append(self.threader.abort())
        self.threader = BackgroundThreader(str(self.index))

    def shutdown(self):
        self.threader.shutdown()
        for a in self.abandoned:
            a.shutdown()

BGThreader = ThreaderManager()
