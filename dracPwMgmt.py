#!/usr/bin/env python
import shlex
import os,sys,re
import string
import socket
import subprocess
import threading
import logger
import logging
import time
from Queue import Queue


LOG = logging.getLogger(__name__)

def displayHelp():
  print("Error argument must be -h for simple host or -f with file")
  print("File must be organized 'hostname IPiDrac'")
  print("Default username is 'root' and password is 'calvin'")
  print("host argument on the commandline must be space-separated")
  print("Usage : dracPowerManagement [ -h <host> ]")
  print("                            [ -f <filename> ]")
  print("                            [ -u <username> ]")
  print("                            [ -p <password> ]")
  sys.exit(1)

# Print executions report
def printReport(report):
   print("#### EXECUTION REPORT ####")
   for host in report:
     print('{} - {}'.format(host,report[host]))
   return True

def queueThread(kwargs,th_number):
  host = kwargs.get('host','localhost')
  #set up the queue to hold all the urls
  q = Queue(maxsize=0)
  for myhost in host:
    q.put(myhost)
  for i in range(th_number):
    LOG.debug('Starting thread %i', i)
    worker = threading.Thread(target=powerRedundancy, args=(q,kwargs.get('user','root'),kwargs.get('password','calvin')))
    worker.setDaemon(True)    #setting threads as "daemon" allows main program to 
                              #exit eventually even if these dont finish correctly 
    worker.start()
   #wait until the queue has been processed
  q.join()
  LOG.debug('All threads completed.')   
  if len(host) > 0 :
    printReport(report)

# When file is specified
def withFile(kwargs):
  try:
    liste = open(kwargs['file'], "r")
  except IOError:
    LOG.error('Impossible douvrir ' + kwargs['file'])
    sys.exit(1)

  # Use many threads (50 max, or one for each url)
  myhost = list()
  for line in liste:
    match1 = re.search(r"\w+\s\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",line)
    match2 = re.search(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",line)
    if match1 or match2: 
      myhost.append(line.split()[len(line.split())-1])
    else:
      LOG.warning("Bad format line {}".format(line))
  LOG.debug("Number of host before treatment: {}".format(len(myhost)))
  num_threads = min(50, len(myhost))
  kwargs['host']=myhost
  queueThread(kwargs,num_threads)
    
# When commandline arguments are specified 
def withArg(kwargs):
  # Use many threads (50 max, or one for each url)
  num_threads = min(50, len(kwargs['host']))
  queueThread(kwargs,num_threads)
    
def CallbackTimeout(p):
  if p.poll() is None:
    p.kill()
    return 'DRAC Timeout'
  else:
    output,error=p.communicate()
    if error:
      return error.split("\n")[0]
    return output.split("\r")[4]

# Change power config via racadm
def powerRedundancy(q,*args):
   while not q.empty():
     work = q.get() 
     myuser,mypass=args[0],args[1]
     if socket.gethostbyname(work):
         cmd=shlex.split(racadm +" -r " + work + " -u " + myuser + " -p " + mypass + " set system.power.RedundancyPolicy 1")
         p=subprocess.Popen(cmd,stdout = subprocess.PIPE, stderr= subprocess.PIPE)
         time.sleep(10)
         output=CallbackTimeout(p)
         LOG.debug("OUTPUT for {} is {}".format(work,output))
         LOG.info("{} {} {}".format(work,myuser,mypass))
         cmd=shlex.split(racadm +" -r " + work + " -u " + myuser + " -p " + mypass + " get system.power.RedundancyPolicy")
         p=subprocess.Popen(cmd,stdout = subprocess.PIPE, stderr= subprocess.PIPE)
         time.sleep(10)
         report[work]=CallbackTimeout(p)
     else:
       LOG.error("Error, host "+ work +" not resolved")
     q.task_done()

if __name__ == '__main__':

  FNULL = open(os.devnull, 'w')
  if subprocess.check_call(['/usr/bin/which','racadm'],stdout=FNULL) != 0:
      LOG.error("Error, racadm introuvable dans le path")
      LOG.error("Maybe PATH=$PATH:/opt/dell/srvadmin could help")
      sys.exit(1)
  else: 
      racadm = subprocess.check_output(['/usr/bin/which','racadm']).split('\n')[0]
  args = {}
  report = {}
  i=1
  while i < len(sys.argv):
     #Multiple host with -h argument
     if sys.argv[i] == '-h': 
       hosts = []
       j=i+1
       while j < len(sys.argv) and sys.argv[j] not in ('-h','-p','-u','-f'):
         hosts.append(sys.argv[j])
         j+=1        
       i=j-2
       args['host']=hosts
     elif sys.argv[i] == '-f':
       args['file'] = sys.argv[i+1]
     elif sys.argv[i] == '-u': 
       args['user'] = sys.argv[i+1]
     elif sys.argv[i] == '-p': 
       args['password'] = sys.argv[i+1]
     else:
        displayHelp()
     i=i+2
  if 'file' in args:
    withFile(args)
    sys.exit(0)
  elif 'host' not in args:
    print('You must specify a host')
    displayHelp()
  else:
    withArg(args)
