import logging
import os
import signal

from dht import Spider
from config import spider_total


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                        datefmt='%a, %d %b %Y %H:%M:%S', )
    spiders = []
    for i in range(spider_total):
        spider = Spider('0.0.0.0', 6886 + i)
        spider.start()
        spiders.append(spider)
    try:
        for spider in spiders:
            spider.join()
    except KeyboardInterrupt:
        for spider in spiders:
            os.kill(spider.pid, signal.SIGKILL)
