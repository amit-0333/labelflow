import time


## a sample job: waits 3 seconds, then returns a message
def sample_job(name):
    time.sleep(3)
    return "Hello " + name