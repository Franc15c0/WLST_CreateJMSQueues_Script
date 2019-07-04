
import sys
from java.lang import System
from java.io import FileInputStream

envconfig=""
if (len(sys.argv) > 1):
	envconfig=sys.argv[1]
else:
	print "Environment Property file not specified"
	sys.exit(2)

confInputStream = FileInputStream(envconfig)
configVars = Properties()
configVars.load(confInputStream)

propInputStream = FileInputStream("WLST_CreateJMSQueues_Properties.properties")
properties = Properties()
properties.load(propInputStream)

print "Starting the script ..."

def isNotBlank (myString):
    return (myString and myString.strip()) 
	
def getVariable(varName):
	var = properties.get(varName)
	if isNotBlank(var):
		return var
	else:
		var = configVars.get(varName)
		if isNotBlank(var):
			return var
		else:
			print "Variable " + varName + " not specified, please check the " + envconfig
			cancelEdit()
			exit()
		
def createUniformQueue(jmsModuleName,jmsModule, qName, qJndiName, qSubdeploymentName, redeliveryLimit, customErrorDest, errorDest):
	mb = getMBean("/JMSSystemResources/" + jmsModuleName + "/JMSResource/" + jmsModuleName + "/UniformDistributedQueues/" + qName)
	
	if not mb:
		udq = jmsModule.createUniformDistributedQueue(qName)
		udq.setJNDIName(qJndiName)
	else:
		udq = getMBean("/JMSSystemResources/" + jmsModuleName + "/JMSResource/" + jmsModuleName + "/UniformDistributedQueues/" + qName)
		print qName + " already exists"
		return
    
	if str(customErrorDest) in ('1'):
		errorQName=qName + "_error"
		errorQJndiName=qJndiName + "_error"
		eUdq = createUniformQueue(jmsModuleName, jmsModule, errorQName, errorQJndiName, qSubdeploymentName, redeliveryLimit, 0, errorDest)
	else:
		if str(errorDest) in ('1'):
			eUdq = getMBean("/JMSSystemResources/" + jmsModuleName + "/JMSResource/" + jmsModuleName + "/UniformDistributedQueues/" + jmsDefaultErrorQueue)
	udq.setForwardDelay(1)
	dfp = udq.getDeliveryFailureParams() 
	if str(customErrorDest) in ('1') or str(errorDest) in ('1'):
		dfp.setErrorDestination(eUdq)
		dfp.setExpirationPolicy('Redirect')
		dfp.setRedeliveryLimit(int(redeliveryLimit))
	dpo = udq.getDeliveryParamsOverrides()
	udq.setSubDeploymentName(qSubdeploymentName)
	udq.addDestinationKey('PriorityDestinationKey')
	print "**************************" + qName + " succesfully created"
	return udq

def createJMSPriorityDestKey(jmsModuleName,jmsModule, dkName):
	mb = getMBean("/JMSSystemResources/" + jmsModuleName + "/JMSResource/" + jmsModuleName + "/DestinationKeys/" + dkName)
	if mb:
		print dkName + " already exists"
		return
	
	destinationkey1 = jmsModule.createDestinationKey(dkName)
	destinationkey1.setSortOrder('Descending')
	destinationkey1.setKeyType('Int')
	destinationkey1.setProperty('JMSPriority')
	print "**************************" + dkName + " succesfully created"

def createConnectionFactory(jmsModuleName,cfName,cfJndiName,subdeploymentName):
	mb = getMBean("/JMSSystemResources/" + jmsModuleName + "/JMSResource/" + jmsModuleName + "/ConnectionFactories/" + cfName)
	if mb:
		print cfName + " already exists"
		return
	
	jmsMySystemResource = getMBean("/JMSSystemResources/" + jmsModuleName)
	theJMSResource = jmsMySystemResource.getJMSResource()
  
	print "Creating Connection Factory ................."
	factory = theJMSResource.createConnectionFactory(cfName)
	factory.setJNDIName(cfJndiName)
	factory.setSubDeploymentName(subdeploymentName)
	trn = factory.getTransactionParams()
	trn.setXAConnectionFactoryEnabled(true)
	lb = factory.getLoadBalancingParams()
	lb.setServerAffinityEnabled(true)
	
	print "Connection Factory " + cfName + " succesfully created"

def createJMSSubdeployment(subdeploymentName, targetServersList, moduleName):
	mb = getMBean('/JMSSystemResources/' + moduleName + '/SubDeployments/' + subdeploymentName)
	if mb:
		print "Subdeployment " + subdeploymentName + " already exists"
		return
		
	jmsMySystemResource = getMBean("/JMSSystemResources/" + moduleName)
	subDep = jmsMySystemResource.createSubDeployment(subdeploymentName)
	TargetArray = String(targetServersList).split(",")
	for Target in TargetArray:
		subDep.addTarget(getMBean('/JMSServers/' + Target))
	
	print "Subdeployment " + subdeploymentName + " succesfully created"
  
def createJMSModule(moduleName, targetCluster, subdeploymentName, targetServersList):
	mb = getMBean("/JMSSystemResources/" + moduleName)
	if mb:
		print "Moduel " + moduleName + " already exists"
		return
	cd('/')
	cmo.createJMSSystemResource(moduleName)
	jmsMySystemResource = getMBean("/JMSSystemResources/" + moduleName)
	jmsMySystemResource.addTarget(getMBean('/Clusters/' + targetCluster))
	print "JMS Module " + moduleName + " succesfully created"
	
	createJMSSubdeployment(subdeploymentName, targetServersList, moduleName)
	
	return jmsMySystemResource
	
def createPersistantStore(storeName, isFileStore, target, dataSource, dsPrefix):
	if isFileStore in ('true'):
		storeType = "FileStore"
	else:
		storeType = "JDBCStore"
		
	mb = getMBean('/' + storeType + 's/' + storeName)
	if mb:
		print storeType + " " + storeName + " already exists"
		return
	
	cd('/')
	if isFileStore in ('true'):
		cmo.createFileStore(storeName)
	else:
		cmo.createJDBCStore(storeName)
		cd('/' + storeType + 's/' + storeName)
		cmo.setDataSource(getMBean('/SystemResources/jdbc.' + dataSource))
		cmo.setPrefixName(dsPrefix)
	
	persistantStore = getMBean('/' + storeType + 's/' + storeName)
	persistantStore.addTarget(target)
	
	print "Persistant Store " + storeName + " succesfully created"
	return persistantStore

def createJmsServer(jmsServerName, persistantStore, target):
	mb = getMBean('/JMSServers/' + jmsServerName)
	if mb:
		print "JMSServers " + jmsServerName + " already exists"
		return
		
	cd('/')
	cmo.createJMSServer(jmsServerName)
	jmsServer = getMBean('/JMSServers/' + jmsServerName)
	jmsServer.setPersistentStore(persistantStore)
	jmsServer.addTarget(target)
	
	print "JMS Server " + jmsServerName + " succesfully created"
	return jmsServer

jmsDefaultErrorQueue=getVariable("jms.Default.Error.Queue")	

print('############################################')
print('      WEBLOGIC CONSOLE CONNECTION           ')
print('############################################')

hostNameConsoleWL = getVariable("hostName.ConsoleWL")
portConsoleWL = getVariable("port.ConsoleWL")
userNameAdmin = getVariable("userName.Admin")
passWordAdmin = getVariable("passWord.Admin")

connect(userNameAdmin,passWordAdmin,'t3://' + hostNameConsoleWL + ':' + portConsoleWL) 

edit()
startEdit()

#############################################################################
#				 				 JMS QUEUES 								#
#############################################################################

print('#######################################################')
print('            PERSISTANT STORES CREATION                 ')
print('#######################################################')

print "Start Creating Persistant Stores and JMS Servers................."
moreServers=1
managedServersCount=1
targetServersList=''
while (moreServers > 0) :
	if isNotBlank(properties.get("ps.Name."+ str(managedServersCount))):
		psName=getVariable("ps.Name."+ str(managedServersCount))
		psIsFileStore=getVariable("ps.isFileStore."+ str(managedServersCount))
		psManagedServer=getVariable("jms.ManagedServer.Name."+ str(managedServersCount))
		psDbStoreJDBC=properties.get("ps.DbStore.JDBC."+ str(managedServersCount))
		psDbStorePrefix=properties.get("ps.DbStore.Prefix."+ str(managedServersCount))
		jmsServerName=getVariable("jmsServer.Name."+ str(managedServersCount))
		managedServersCount = managedServersCount + 1
		mbServer = getMBean("Servers/" + psManagedServer)
		print "Creating "+ psName +"..."
		persistantStore = createPersistantStore(psName, psIsFileStore, mbServer, psDbStoreJDBC, psDbStorePrefix)
		print "Creating JMS Server " + jmsServerName
		createJmsServer(jmsServerName, persistantStore, mbServer)
		if isNotBlank(targetServersList):
			targetServersList = targetServersList + ',' + jmsServerName
		else:
			targetServersList = jmsServerName
	else:
		moreServers = 0

print('#######################################################')
print('        MODULE AND SUBDEPLOYMENT CREATION              ')
print('#######################################################')
print "Creating JMS Module and Subdeployment................."
jmsModuleName=getVariable("jms.Module.Name")
jmsModuleTarget=getVariable("jms.Cluster.Name")
jmsSubdeploymentName=getVariable("jms.Subdeployment.Name")
createJMSModule(jmsModuleName,jmsModuleTarget,jmsSubdeploymentName,targetServersList)

print('#######################################################')
print('            CONNECTION FACTORY CREATION                ')
print('#######################################################')

print "Start Creating Connection Factory................."
jmsConnectionFactoryName=getVariable("jms.ConnectionFactory.Name")
createConnectionFactory(jmsModuleName,jmsConnectionFactoryName,jmsConnectionFactoryName,jmsSubdeploymentName)



print('#######################################################')
print('                JMS QUEUES CREATION                    ')
print('#######################################################')

jmsQueuesCount=1
jmsMySystemResource = getMBean("/JMSSystemResources/" + jmsModuleName)
theJMSResource = jmsMySystemResource.getJMSResource()
jmsPriorityDestKey=getVariable("jms.Priority.Dest.Key")
createJMSPriorityDestKey(jmsModuleName,theJMSResource,jmsPriorityDestKey)
while (jmsQueuesCount > 0) :
	if isNotBlank(properties.get("queue.Name."+ str(jmsQueuesCount))) :
		qName=getVariable("queue.Name." + str(jmsQueuesCount))
		qJndiName=getVariable("queue.JndiName." + str(jmsQueuesCount))
		qRedeliveryLimit=getVariable("queue.RedeliveryLimit." + str(jmsQueuesCount))
		qCustomErrorDest=getVariable("queue.CustomErrorDest." + str(jmsQueuesCount))
		qErrorDest=getVariable("queue.ErrorDest." + str(jmsQueuesCount))
		print "Creating JMS Queue " + qName
		createUniformQueue(jmsModuleName,theJMSResource,qName,qJndiName,jmsSubdeploymentName,qRedeliveryLimit,qCustomErrorDest,qErrorDest)
		jmsQueuesCount = jmsQueuesCount + 1
	else :
		jmsQueuesCount = 0

try:
	save()
	activate(block="true")
	print "Script returns SUCCESS"   
except:
	print "Error while trying to save and/or activate!!!"
	cancelEdit()
	dumpStack()
exit()