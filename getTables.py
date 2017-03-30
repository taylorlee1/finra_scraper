#! /usr/bin/env python2

import hashlib
import pandas as pd
import os,sys
import time
from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


import csv

import threading
import subprocess

import logging

logfile = 'finra.tables.log'
logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s %(processName)s%(threadName)s %(levelname)s %(message)s',
                            datefmt='%m-%d %H:%M',
                            filename=logfile,
                            filemode='w')

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(processName)s%(threadName)s %(levelname)s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)


WIFI_SITE = 'http://otce.finra.org/DLDeletions'
script_path = os.path.dirname(os.path.abspath( __file__ ))
os.environ["PATH"] += os.pathsep + script_path
logging.info("ENV PATH: %s" % (os.environ["PATH"]))

def setupDisplay():
    display = Display(visible=0, size=(1600, 900))
    display.start()
    return display

def getXpath(xpath, b):
    try:
        E = b.find_element_by_xpath(xpath)
        return E
    except Exception as e:
        logging.error(("%s Exception: %s" % (xpath, e)))
    return None

def getClassS(cls, b):
    try:
        F = b.find_elements_by_class_name(cls)
        return F
    except Exception as e:
        logging.error(("%s Exception: %s" % (cls, e)))
    return None

def getSelS(sel, b):
    try:
        F = b.find_elements_by_css_selector(sel)
        return F
    except Exception as e:
        logging.error(("%s Exception: %s" % (cls, e)))
    return None

def getHeader(browser):
    logging.info("getHeader()")
    xpath='//*[@id="tblDLD"]/thead/tr'

    E = getXpath(xpath, browser)
    cls = "DataTables_sort_wrapper"
    F = getClassS(cls, E)

    logging.info("F len: %s" % (len(F)))
    h = list()
    for f in F:
        logging.info(f.text)
        h.append(f.text)
    return h
    
def getData(browser):
    logging.info("getData()")

    xpath='//*[@id="tblDLD"]/tbody'
    E = getXpath(xpath, browser)
    h = list()

    for tr in getSelS('tr', browser):
        row = list()
        for td in getSelS('td', tr):
            #logging.info(td.text)
            row.append(td.text)

        if len(row) > 0 and row[0] != u'':
            h.append(row)

    return h
            


def tableDump(browser):
    logging.info("tableDump()")
    header = getHeader(browser)
    logging.info("header: %s" % (header))
    data = getData(browser)

    logging.info("%s" % (header))
    for d in data:
        logging.info("%s" % (d))
    return [header] + data

def parseDate(browser,date):

    url=WIFI_SITE
    browser.get(url)

    xpath='//*[@id="DateRangeStart"]'

    try:
        E = browser.find_element_by_xpath(xpath)
    except Exception as e:
        logging.error(("%s Exception: %s" % (xpath, e)))
        return

    E.clear()
    E.send_keys(date + Keys.RETURN)

    browser.save_screenshot('000.png')

    D = dict()
    pageCount = 0
    nextXpath = "//div[contains(text(), 'Next')]"

    while True:
        #slep = getXpath('//*[@id="tblFooter"]/div[1]',browser)
        #if slep:
        #    logging.info("%s" % (slep.text))
        d = tableDump(browser)
        E = getXpath(nextXpath, browser)
        if not E:
            logging.info("No more pages, quit")
            break
        else:
            logging.info("Next: %s" % (E.text))
            D[pageCount] = d
            pageCount += 1

            wait = WebDriverWait(browser, 10)
            element = wait.until(EC.element_to_be_clickable((By.XPATH, nextXpath)))

            actions = ActionChains(browser)
            actions.move_to_element(E)
            actions.perform()
            time.sleep(5)
            actions.reset_actions()
            actions.click()
            keepClicking(E)
            
        #if len(D) > 3:
        #    break
    return D

def keepClicking(E):
    while True:
        try:
            E.click()
            time.sleep(5)
        except Exception as e:
            logging.info("Couldn't keep clicking, probably good now %s" % (e))
            return


def dumpToFile(d):
    outfile = 'out.csv'
    headerDone = False
    with open(outfile, 'w') as f:
        for page in d:
            logging.info("page: %s" % (d[page]))
            if not headerDone:
                f.write(','.join(d[page][0]) + "\n")
                headerDone = True

            for i in xrange(1,len(d[page])):
                f.write(','.join(d[page][i]) + "\n")

    logging.info("wrote %s" % (outfile))

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("need an arg")
        sys.exit(1)

    proc=None
    #proc = subprocess.Popen(["java", "-jar", "selenium-server.jar"])

    display = setupDisplay()

    caps = DesiredCapabilities.FIREFOX
    caps['marionette']=True
    caps['binary']='/usr/lib/firefox-trunk/firefox-trunk'
    geckodriver='/home/nigro/tmp/usps_boxes/geckodriver'
    browser = webdriver.Firefox(capabilities=caps, executable_path=geckodriver)
    browser.implicitly_wait(10)

    data = parseDate(browser,sys.argv[1])
    dumpToFile(data)

    browser.quit()
    display.stop()
    if proc:
        proc.terminate()
        proc.wait()

