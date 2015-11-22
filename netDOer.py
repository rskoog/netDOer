#
# NetDOer Class A class to make a couple network tasks easier.
#
# This script uses the paramiko expect library 
# https://github.com/fgimian/paramiko-expect
# It was however tested against my local fork which includes a couple of changes
# https://github.com/rskoog/paramiko-expect
#

import re
import traceback
import paramiko
from paramikoe import SSHClientInteraction

JUNOS_MATCH = ".*--- JUNOS.*"
JUNOS_SHELL = ".*% $"
PROMPT = ".*(>|#) ?"
PAGER_PROMPT = ".*((--More-- )|(---\(more ?\d?\d?%?\)---))"
ENABLE_PASS_PROMPT = ".*password: "
firstexpectvalues = [JUNOS_MATCH, JUNOS_SHELL, PROMPT, ENABLE_PASS_PROMPT]
expectprompt = [PROMPT, ENABLE_PASS_PROMPT, PAGER_PROMPT]

class netDOer:
   """This class interacts with a network device using an SSH connection, 
   currently attempts to support IOS like devices and Junos devices"""

   def __init__(self, user, password, host, enablepass, timeout=60, 
                display=False):
       """Constructor for NetDOer class.

       Arguments:
       user - user to connect with
       password - password to connect to device with
       host - host device to connect to.
       timeout - timeout for connection

       The constructed object will already be in privleged mode after
       the object is initialized if the devie is IOSlike.
       """

       try:
           #Create paramiko session to device, it must be attached to object
	   #so it isn't closed.
           self.SSHclient = paramiko.SSHClient()
	   self.SSHclient.load_system_host_keys()
	   self.SSHclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	   self.SSHclient.connect(hostname=host, username=user, 
	                           password=password)
           self.SSHinteraction = SSHClientInteraction(self.SSHclient, 
	                                              timeout=timeout,
						      display=display)
	   self.DeviceType = False
	   while True:
	       self.SSHinteraction.expect(firstexpectvalues)
	       #We saw JUNOS after login so the device is juniper
	       if self.SSHinteraction.last_match == JUNOS_MATCH:
	           self.DeviceType = "junos"
		   #We need to see if we have the cli or shell
		   junosshellre = re.compile(JUNOS_SHELL)
		   match = junosshellre.search(
		                        self.SSHinteraction.current_output)
		   junospromptre = re.compile(PROMPT)
		   promptmatch = junospromptre.search(
		                 self.SSHinteraction.current_output)
	           if match: 
	               #we have the shell need the CLI
	               self.SSHinteraction.send("cli")
		   elif promptmatch:
		       #we have a prompt and are good to go.
		       break
	       #We have a prompt and no device type yet.
	       elif (self.SSHinteraction.last_match == PROMPT and not 
	             self.DeviceType):
	           self.DeviceType = "cisco"
	           self.SSHinteraction.send("enable")
	       #We need to send the enable pass
	       elif self.SSHinteraction.last_match == ENABLE_PASS_PROMPT:
	           self.SSHinteraction.send(enablepass)
	       elif self.SSHinteraction.last_match == JUNOS_SHELL:
	           #we got the junos shell need to get in the cli
		   self.SSHinteraction.send("cli")
	       #We have the device type and a prompt
	       elif ((self.SSHinteraction.last_match == PROMPT or 
	            self.SSHinteraction.last_match == JUNOS_PROMPT) and
	             self.DeviceType):
	           break
       except:
           raise ValueError("Failed to connect to Device and initialize obj")
	   pass

   def __getJuniperValue(self, commandstring):
       #Juniper values just happen to be 
       #in the same position sometimes, lets take advantage.
       self.SSHinteraction.send(commandstring)
       self.SSHinteraction.expect(expectprompt)
       linesofoutput = self.SSHinteraction.current_output.split('\n')
       wordsofoutput = linesofoutput[1].split()
       return wordsofoutput[1]

   def __getCiscoCommandOutput(self, commandstring):
       #cisco commands can gennerate a lot of output but their pager at least
       #handles better than juniper.
       self.SSHinteraction.send(commandstring)
       self.SSHinteraction.expect(expectprompt)
       outputToReturn = self.SSHinteraction.current_output_clean
       while self.SSHinteraction.last_match == PAGER_PROMPT:
           self.SSHinteraction.send("")
	   self.SSHinteraction.expect(expectprompt)
	   outputToReturn += self.SSHinteraction.current_output_clean
       return outputToReturn

   def __setCiscoSetting(self, commandstring):
       self.SSHinteraction.send("configure terminal")
       self.SSHinteraction.expect(expectprompt)
       self.SSHinteraction.send(commandstring)
       self.SSHinteraction.expect(expectprompt)
       invalidcommandre = re.compile("Invalid input detected at")
       commandfailed = invalidcommandre.search(
                                         self.SSHinteraction.current_output)
       self.SSHinteraction.send("end")
       self.SSHinteraction.expect(expectprompt)
       if commandfailed:
           raise ValueError("IOS command was invalid")
       #The command was applied.
       return 0

   def __setJuniperSetting(self, commandstring):
       self.SSHinteraction.send("edit")
       self.SSHinteraction.expect(expectprompt)
       self.SSHinteraction.send(commandstring)
       self.SSHinteraction.expect(expectprompt)
       invalidcommandre = re.compile("(syntax error)|(unknown command)")
       commandfailed = invalidcommandre.search(
                                        self.SSHinteraction.current_output)
       if commandfailed:
           #our command wasn't recognized we need to get out of edit and raise
	   #an error.
	   self.SSHinteraction.send("exit")
	   self.SSHinteraction.expect(expectprompt)
	   raise ValueError("Junos didn't recognize the command")

       else:
           #our command worked we can try to commit.
	   self.SSHinteraction.send("commit")
	   self.SSHinteraction.expect(expectprompt)
	   commitre = re.compile("commit complete")
	   commitsuccess = commitre.search(self.SSHinteraction.current_output)
	   if commitsuccess:
	       #it worked.
	       self.SSHinteraction.send("exit")
	       self.SSHinteraction.expect(expectprompt)
	       return 0
	   else:
	       #we need to rollback the commit failed
	       self.SSHinteraction.send("rollback 0")
	       self.SSHinteraction.expect(expectprompt)
	       self.SSHinteraction.send("exit")
	       self.SSHinteraction.expect(expectprompt)
	       raise ValueError("Junos was unable to commit the change")

   def getSerial(self):
       """Returns the serial number of a device
       Arguments self
       Returns serial number for a device""" 
       if self.DeviceType =="junos":
           return self.__getJuniperValue(
	           "show chassis hardware | match Chassis")
       if self.DeviceType =="cisco":
           inventory = self.__getCiscoCommandOutput("show inventory")
	   inventorylines = inventory.split("\n")
	   words = inventorylines[1].split()
	   return words[6]

   def getModel(self):
       """Returns model number of switch
       Arguments self
       returns string value for model of switch"""
       if self.DeviceType == "junos":
           return self.__getJuniperValue("show version | match Model")
       if self.DeviceType =="cisco":
           inventory = self.__getCiscoCommandOutput("show inventory")
	   inventorylines = inventory.split("\n")
	   words = inventorylines[1].split()
	   return words[1]

   def getHostname(self):
       """Returns hostname of device
       Arguments self
       returns string value for hostname"""
       if self.DeviceType =="junos":
	   return self.__getJuniperValue("show version | match Hostname")
       if self.DeviceType =="cisco":
           config = self.__getCiscoCommandOutput("show run | inc hostname")
	   #in case there were two matches
	   configlines = config.split("\n")
	   configwords = configlines[0].split()
	   return configwords[1]

   def getInterfaceList(self):
       #Cleaning up the output after handling the paging is going to take
       #effort skipping for now.
       if self.DeviceType =="junos":
           self.SSHinteraction.send("set cli screen-length 0")
	   self.SSHinteraction.expect(expectprompt)
	   self.SSHinteraction.send("show interfaces terse")
	   self.SSHinteraction.expect(expectprompt)
	   #returning a bunch of text.
	   return self.SSHinteraction.current_output_clean
       if self.DeviceType == "cisco":
           return self.__getCiscoCommandOutput("show ip interface brief")

   def setHostname(self, hostname):
       if self.DeviceType == "junos":
           command = "set system host-name " + hostname
	   return self.__setJuniperSetting(command)
       if self.DeviceType == "cisco":
           command = "hostname " + hostname
	   return self.__setCiscoSetting(command)

   def setSNMPv2(self, community, write=False):
       if self.DeviceType =="junos":
           command = "set snmp community " + community
           if write:
	       command += " authorization read-write"
	   else:
	       command += " authorization read-only"
	   return self.__setJuniperSetting(command)
       if self.DeviceType == "cisco":
           command = "snmp-server community " + community
	   if write:
	       command += " RW"
	   else:
	       command += " RO"
	   return self.__setCiscoSetting(command)

   def setNTPserver (self, ntpserver):
       if self.DeviceType =="junos":
           command = "set system ntp server " + ntpserver
	   return self.__setJuniperSetting(command)
       if self.DeviceType == "cisco":
           command = "ntp server " + ntpserver
	   return self.__setCiscoSetting(command)
	   
