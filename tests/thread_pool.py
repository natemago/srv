from concurrent.futures import ThreadPoolExecutor as ThreadPoolExecutor, as_completed
import time, random

executor = ThreadPoolExecutor(max_workers=500)

def do_async(id, sleep_timeout):
    print("[%d] about to sleep %d seconds" %(id, sleep_timeout))
    time.sleep(sleep_timeout)
    print("[%d] woke up - and exiting"%id)
    
    
n = 0
while n <= 1000:
    to = random.randint(1,5)
    print("Setting up %d -> %d" %(n, to))
    executor.submit(do_async, n, to)
    n = n + 1