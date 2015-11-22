#!/usr/local/bin/python2.7
"""This is an example script I wrote using the netDOer class I wrote for this
assignment.
"""
import getpass
import traceback
from netDOer import *
import argparse

def main():
   parser = argparse.ArgumentParser(description="an example script showing the"
                                                " netDOer class")
   parser.add_argument("-p", dest="password", type=str, help="Password to be "
                       "used for the device. The script will prompt if not "
		       "given one")
   parser.add_argument("-enablepass", dest="enablepass", type=str,
                       help="Enable password, defaults to the same as "
		       "password.")
   parser.add_argument("-getvalues", dest="getvalues", type=bool, default=True,
                       help="Enables the get values part of script, by default"
		       " this is set to True.")
   parser.add_argument("-setntp", dest="setntp", type=str, help="NTP server to"
                       " set.")
   parser.add_argument("-sethost", dest="sethost", type=str, help="Hostname to"
                       " set.")
   parser.add_argument("-setsnmp", dest="setsnmp", type=str, help="SNMP "
                       "community to use when setting SNMP")
   parser.add_argument("-setwrite", dest="setwrite", type=bool, default=False,
                       help="Makes the SNMP community writable, by default it "
		       " is read only.Set to True to enble write.")
   parser.add_argument("-t", dest="timeout", type=int, default=10,
                       help="Time allowed to connect to the device.")
   parser.add_argument("-u", dest="username", type=str,
                       default=getpass.getuser() , help="Username to be "
		       "used for the device, defaults to current user.")
   parser.add_argument("-r", dest="routerFile", type=str, help="Specifies a"
                       " file with a list of routers to run against. "
		       "This option overrides the router argument.")
   parser.add_argument("router", metavar="router", type=str,
                      nargs=argparse.REMAINDER, help="One or my routers to "
		      "connect to.")
   args = parser.parse_args()

   #prompt for pass if one wasn't given.
   if not args.password:
       password = getpass.getpass()
   else:
       password = args.password
   #check to see if we were given an enable pass and if so set the enable, if
   #none default to same password.
   if args.enablepass:
       enablePassword = args.enablepass
   else:
       enablePassword = password
   #check to see if the routers were specified with a file or directly through 
   #the cli.  Then create the router list.
   if args.routerFile:
       routerFileObj = open(args.routerFile)
       routerList = routerFileObj.read().splitlines()
       routerFileObj.close()
   else:
       routerList = args.router
   #Counnter to determine which router we are working with
   routerId = 0
   while routerId < len(routerList):
       try:
           #Create a new netDOer obj
           router = netDOer(args.username,password,routerList[routerId],
                            enablePassword, timeout=args.timeout)
           if args.getvalues:
	       print (router.getHostname() + " " + router.getModel() + " " +
	              router.getSerial() + "\n")
	       print router.getInterfaceList()
           if args.setntp:
	       router.setNTPserver(args.setntp)
	   if args.sethost:
	       router.setHostname(args.sethost)
	   if args.setsnmp:
	       router.setSNMPv2(args.setsnmp, args.setwrite)    
       except:
           print "-------------------------- Device Error --- \n"
           print "There was a problem with " + routerList[routerId] + "\n"
           traceback.print_exc()
	   print "-------------------------- Next Device ---- \n"
	   pass
       routerId += 1
if __name__ == '__main__':
   main()




