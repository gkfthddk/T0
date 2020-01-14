#!/usr/bin/env python
"""
Hopefully someone is going to refactor these scripts at some point.
"""
print("replayWorkflowStatus.py")
import cx_Oracle
import time
import sys
import os
from jira import JIRA, JIRAError
from jiraReporting import JiraReporting


# Initial configuration
# Authentication credentials
jira_cookie = '/data/tier0/jenkins/jiraBiscuit.txt'

jira_url = 'https://its.cern.ch/jira'
headers = {'Accept': 'application/json'}
proxy = '/data/certs/proxy.pem'

# CMSWeb and JIRA instances
jira_project_prod = "CMSTZ"
jira_project_test = "CMSTZDEV"

#Email configuration
mail_address = "cms-tier0-monitoring-alerts@cern.ch"
mail_subject = "Jenkins automatic replay"

#Jira watchers list. Should be updated with present T0 team
watchers = ['anquinte', 'vjankaus', 'yulee']
labels = ['Tier0_Replays']
print("Running t0 workflow replay with python3")

def getT0astCreds():
    print("getT0astCreds")
    home="/data/tier0/admin/"
    fileName="WMAgent.secrets"
    ORACLE_USER=""
    ORACLE_PASS=""
    ORACLE_TNS=""
    try:
        with open(home+fileName) as f:
            for line in f:
                if line.startswith("ORACLE_USER"):
                    ORACLE_USER=line.strip().split("=")[-1]
                elif line.startswith("ORACLE_PASS"):
                    ORACLE_PASS=line.strip().split("=")[-1]
                elif line.startswith("ORACLE_TNS"):
                    ORACLE_TNS=line.strip().split("=")[-1]
    except IOError:
        print("Attempted to get Oracle pass")
        print("Could not read file:", home+fileName)

    return [ORACLE_USER,ORACLE_PASS,ORACLE_TNS]

#check the number of workflows by type Repack/Express
def getWorkflowCount(creds, workflowName):
    #print("getWorkflowCount",)
    dbconn = cx_Oracle.connect(creds[0], creds[1], creds[2])
    cursor = dbconn.cursor() 
    #Get a number of workflows in progress 
    query = "SELECT DISTINCT name FROM dbsbuffer_workflow WHERE completed = 0 AND name like '%" + workflowName +"%'"
    cursor.execute(query)
    result = cursor.fetchall() #[(name),(name),]
    #print("During {} process...".format(workflowName))
    #print("Current Workflow list : ",result)
    return result

#check the number of filesets on DB
def getFilesets(creds):
    #print("getFilesets")
    dbconn = cx_Oracle.connect(creds[0], creds[1], creds[2])
    cursor = dbconn.cursor()
    #Get a number of filesets
    #query = "SELECT COUNT(*) FROM wmbs_fileset"
    query = "SELECT id, name, open FROM wmbs_fileset"
    #query = "SELECT * FROM wmbs_fileset"
    cursor.execute(query)
    result = cursor.fetchall() #[(id,name),(id,name),]
    
    #print("Fileset list : ",result)
    return result

def getPaused(creds):
    #print("getPaused")
    dbconn = cx_Oracle.connect(creds[0], creds[1], creds[2])
    cursor = dbconn.cursor() 
    #Get a number of paused jobs
    query =  "SELECT id, name, cache_dir FROM wmbs_job WHERE state = (SELECT id FROM wmbs_job_state WHERE name = 'jobpaused')"
    #print(query)
    cursor.execute(query)
    result = cursor.fetchall() #[(id,name,cache_dir),(id,name,cache_dir),]
    #print("Paused list : ",result)
    return result

def getJobs(creds):
    dbconn = cx_Oracle.connect(creds[0], creds[1], creds[2])
    cursor = dbconn.cursor() 
    #Get a number of paused jobs
    #query =  "SELECT name,id FROM wmbs_job_state" #wmbs_jobs_state.id error
    query =  "SELECT id, name,state FROM wmbs_job" #wmbs_jobs_state.id error
    #print(query)
    cursor.execute(query)
    result = cursor.fetchall() #[(id,name,cache_dir),(id,name,cache_dir),]
    #print("job list : ",result)
    return result

def main():
    """
    _main_
    Script's main function:
        check until all Express or Repack workflows are done.
    """
    jiraReporting = JiraReporting()
    jira_instance = jira_project_test

    #load cookies
    cj = jiraReporting.loadCookies(jira_cookie)

    #Get the proxy
    proxy_info = jiraReporting.getProxy(proxy)
    print("proxy info",proxy_info)

    #Initialize JIRA instance 
    jira = JIRA(jira_url)
    jira._session.cookies = cj
    
    print(sys.argv)
    if len(sys.argv) == 8:
        buildNumber = sys.argv[1]
        hostName = os.popen('hostname').read().rstrip()
        print("hostname : ", hostName)
        jobname = sys.argv[2]
        prTitle = sys.argv[3]
        prMessage = sys.argv[4]
        prLink = sys.argv[5]
        buildurl = sys.argv[6]
        calljira = int(sys.argv[7])
        if(calljira):print("Jira reporting is open.")
        else:print("Jira reporting is ignored.")

        print("buildNumber : ",buildNumber)
        print("Pull request title : ",prTitle)
        print("Pull request message : ",prMessage)
        print("Pull request link : ",prLink)
        print("build url : ",buildurl)
        ticketDescription = """Configuration for the replay is available at : {}
The status of this build can be found at : {}.
""".format(prLink,buildurl)
        subject = "Tier0_REPLAY v{} {} on {}. {}".format(str(buildNumber),jobname,hostName,prTitle)
        #create a new JIRA issue
        if(calljira):newIssue = jiraReporting.createJiraTicket(jira, jira_instance, subject, ticketDescription, labels, watchers)
        if(calljira):firstComment = jiraReporting.addJiraComment(jira, jira_instance, newIssue, "The replay has started. Its progress will be reported here.")
        print(ticketDescription)
    # To stop sending emails, comment out the line below
    # send an email with the summary of Jira issues
    #sendEmailAlert(tickets, sources, extraComment)
    state_dic={1:'created',2:'createcooloff',3:'jobfailed',4:'cleanout',5:'killed',
                6:'complete',7:'submitfailed',8:'submitcooloff',9:'retrydone',10:'none',
                11:'submitpaused',12:'jobcooloff',13:'executing',14:'success',15:'createpaused',
                16:'new',17:'jobpaused',18:'createfailed',19:'exhausted'}
    creds=getT0astCreds()
    repackWorkflowCount = 1
    expressWorkflowCount = 1
    processing = True
    expressProcessing = True
    repackProcessing = True
    print("Befor processing, Fileset list : ",getFilesets(creds))
    timing=0
    while processing:
        filesetList = getFilesets(creds)
        filesetCount = len(filesetList)
        #print("fileset count {}".format(filesetCount))
        #if(timing%30):
        #    print("getJobs")
        #    dump=getJobs(creds)
        if filesetCount == 0:
            try:
                if(calljira):jiraReporting.addJiraComment(jira, jira_instance, newIssue, "All filesets were closed.")
                print("All filesets were closed.")
            except Exception as e:
                print(e)
                print("Unable to comment JIRA issue 0. Check fileset closed message")
        else:
            print("Fileset left {}".format(filesetCount))
            if(timing>30 and timing%60==0):
                print("Fileset list : ",filesetList)
                exfilesetList=filesetList
                if(timing>300 and exfilesetList==filesetList):
                    print("It takes too long without changes")
                    exit(-1)
                if(timing>720):
                    print("It's been over 12 hours, fails.")
                    exit(-1)
                    
        timing+=1
        pausedList = getPaused(creds)
        pausedCount = len(pausedList)
        
        if pausedCount != 0:
            pausedMessage="*There are {} paused jobs in the replay.*".format(pausedCount)
            try:pausedMessage="\n".join(["{} : {}".format(pausedName[0],pausedName[1]) for pausedName in pausedList])
            except:print(pausedList)
            pausedMessage="*There are {} paused jobs in the replay.* List of Paused job below.".format(pausedCount)+pausedMessage
            print(pausedMessage)
            print(pausedList)
            try:
                if(calljira):jiraReporting.addJiraComment(jira, jira_instance, newIssue, pausedMessage)
                if(calljira):jiraReporting.addJiraComment(jira, jira_instance, newIssue, "Replay was closed by paused job")
                print("Replay was closed by paused job")
                sys.exit(1)
            except Exception as e:
                print(e)
                print("Unable to comment JIRA issue 1. Check Paused jobs message")
        if filesetCount == 0 and pausedCount == 0:
            try:
                if(calljira):jiraReporting.addJiraComment(jira, jira_instance, newIssue, "*There was NO paused job in the replay.*")
                if(calljira):jiraReporting.addJiraComment(jira, jira_instance, newIssue, "*Replay was successful.*")
                print("*Replay was successful.*")
                sys.exit(0)
            except Exception as e:
                print(e.message, e.args)
                print("There were errors when the replay has already finished.")
                print("Unable to comment JIRA issue 2. Check success message")
        if repackProcessing:
            print("Checking Repack workflows... repackworkflowcount {}".format(repackWorkflowCount))
            if repackWorkflowCount > 0:
                repackworkflowList = getWorkflowCount(creds, "Repack")
                if(timing%3==0):
                    print("Repack Workflow list : ",repackworkflowList)
                    current_jobs=getJobs(creds)
                    print("getJobs ",[[current_job[0],current_job[1],state_dic[current_job[2]]] for current_job in current_jobs])
                repackWorkflowCount = len(repackworkflowList)
            else:
                try:
                    if(calljira):jiraReporting.addJiraComment(jira, jira_instance, newIssue, "All Repack workflows were processed.")
                    print("All Repack workflows were processed.")
                except Exception as e:
                    print(e)
                    print("Unable to comment JIRA issue 3. Check repack processed message")
                repackProcessing = False
        if expressProcessing:
            print("Checking Express workflows...")
            if expressWorkflowCount > 0:
                expressWorkflowList = getWorkflowCount(creds, "Express")
                print("Express Workflow list : ",expressWorkflowList)
                expressWorkflowCount = len(expressWorkflowList)
            else:
                try:
                    if(calljira):jiraReporting.addJiraComment(jira, jira_instance, newIssue, "All Express workflows were processed.")
                    print("All Express workflows were processed.")
                except Exception as e:
                    print(e)
                    print("Unable to comment JIRA issue 4. Check express processed message")
                expressProcessing = False
        time.sleep(60)

if __name__ == "__main__":
    main()

    
