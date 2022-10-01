
# Class which will run the main loop of the program 

from unittest import result
import pexpect
import pexpect.replwrap
import time
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

PEXPECT_PROMPT = u'[PEXPECT_PROMPT>'
PEXPECT_CONTINUATION_PROMPT = u'[PEXPECT_PROMPT+'

class Executor:
    shell = None
    markdownData = None
    executableCodeList = None

    def __init__(self, markdownData):
        self.markdownData = markdownData
        self.executableCodeList = {"bash", "terraform", 'azurecli-interactive' , 'azurecli'}
        self.shell = self.get_shell()

    # Fairly straight forward main loop. While markdownData is not empty
    # Checks type for heading, code block, or paragrpah. 
    # If Heading it outputs the heading, pops the item and prompts input from user
    # If paragraph it outputs paragraph and pops item from list and continues with no pause
    # If Code block, it calls ExecuteCode helper function to print and execute the code block
    def runMainLoop(self):
        beginningHeading = True
        fromCodeBlock = False
        while len(self.markdownData) > 0:

            if (self.markdownData[0][0] == '#'):
                if beginningHeading or fromCodeBlock:
                    print(self.markdownData[0][1].value)
                    self.markdownData.pop(0)
                    beginningHeading = False
                    fromCodeBlock = False
                
                else:
                    beginningHeading = True
                    print("\n\nPress any key to continue... Press b to exit the program \n \n")
                    keyPressed = self.getInstructionKey()
                    if keyPressed == 'b':
                        print("Exiting program on b key press")
                        break

            elif (self.markdownData[0][0] == 'p'):
                print(self.markdownData[0][1].value)
                self.markdownData.pop(0)


            elif (self.markdownData[0][0] == '```'):
                print('```' + self.markdownData[0][1].subtype + '\n' + self.markdownData[0][1].value + '\n```')
                self.executeCode()
                self.markdownData.pop(0)
                fromCodeBlock = True
                
            else:
                self.markdownData.pop(0)


    # Checks to see if code block is executable i.e, bash, terraform, azurecli-interactive, azurecli
    # If it is it will wait for input and call run command which passes the command to the repl
    def executeCode(self):
        if self.markdownData[0][1].subtype in self.executableCodeList:
            print("\n\nPress any key to execute the above code block... Press b to exit the program \n \n")
            keyPressed = self.getInstructionKey()
            if keyPressed == 'b':
                print("Exiting program on b key press")
                exit()
            self.runCommand()
           
            
        else:
            print("\n\nPress any key to continue... Press b to exit the program \n \n")
            keyPressed = self.getInstructionKey()
            if keyPressed == 'b':
                print("Exiting program on b key press")
                exit()

    # Function takes a command and uses the shell which was instantiated at run time using the 
    # Local shell information to execute that command. If the user is logged into az cli on 
    # The authentication will carry over to this environment as well 
    def runCommand(self):
        command = self.markdownData[0][1].value
        expectedResult = self.markdownData[0][1].results
        expectedSimilarity = self.markdownData[0][1].similarity

        #print("debug", "Execute command: '" + command + "'\n")
        startTime = time.time()
        response = self.shell.run_command(command).strip()
        timeToExecute = time.time() - startTime
        print("\n" + response + "\n" + "Time to Execute - " + str(timeToExecute))

        print("Expected Results - " + expectedResult)
        if expectedResult is not None:
            self.testResponse(response, expectedResult, expectedSimilarity)
        
        print("\n\nPress any key to continue... Press b to exit the program \n \n")
        keyPressed = self.getInstructionKey()
        if keyPressed == 'b':
            print("Exiting program on b key press")
            exit()

    def testResponse(self, response, expectedResult, expectedSimilarity):
        # Todo... try to implement more than just fuzzy matching. Can we look and see if the command returned 
        # A warning or an error? Problem I am having is calls can return every type of response... I could 
        # Hard code something for Azure responses, but it wouldn't be extendible

        #print("\n```output\n" + expectedResult + "\n```")

        actualSimilarity = fuzz.ratio(response, expectedResult) / 100
        if actualSimilarity < float(expectedSimilarity):
            print("The output is NOT correct. The remainder of the document may not function properly")
            print("Expected Similarity - " + expectedSimilarity)
            print("Similarity score is " + str(actualSimilarity))
           
    
    
    def getInstructionKey(self):
        """Waits for a single keypress on stdin.
        This is a silly function to call if you need to do it a lot because it has
        to store stdin's current setup, setup stdin for reading single keystrokes
        then read the single keystroke then revert stdin back after reading the
        keystroke.
        Returns the character of the key that was pressed (zero on
        KeyboardInterrupt which can happen when a signal gets handled)
        This method is licensed under cc by-sa 3.0 
        Thanks to mheyman http://stackoverflow.com/questions/983354/how-do-i-make-python-to-wait-for-a-pressed-key\
        """
        import termios, fcntl, sys, os
        fd = sys.stdin.fileno()
        # save old state
        flags_save = fcntl.fcntl(fd, fcntl.F_GETFL)
        attrs_save = termios.tcgetattr(fd)
        # make raw - the way to do this comes from the termios(3) man page.
        attrs = list(attrs_save) # copy the stored version to update
        # iflag
        attrs[0] &= ~(termios.IGNBRK | termios.BRKINT | termios.PARMRK 
                      | termios.ISTRIP | termios.INLCR | termios. IGNCR 
                      | termios.ICRNL | termios.IXON )
        # oflag
        attrs[1] &= ~termios.OPOST
        # cflag
        attrs[2] &= ~(termios.CSIZE | termios. PARENB)
        attrs[2] |= termios.CS8
        # lflag
        attrs[3] &= ~(termios.ECHONL | termios.ECHO | termios.ICANON
                      | termios.ISIG | termios.IEXTEN)
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
        # turn off non-blocking
        fcntl.fcntl(fd, fcntl.F_SETFL, flags_save & ~os.O_NONBLOCK)
        # read a single keystroke
        try:
            ret = sys.stdin.read(1) # returns a single character
        except KeyboardInterrupt:
            ret = 0
        finally:
            # restore old state
            termios.tcsetattr(fd, termios.TCSAFLUSH, attrs_save)
            fcntl.fcntl(fd, fcntl.F_SETFL, flags_save)
        return ret

        
    def get_shell(self):
        """Creates the shell in which to run commands for the 
            innovation engine 
        """
        if self.shell == None:
            child = pexpect.spawnu('/bin/bash', echo=False, timeout=None)
            ps1 = PEXPECT_PROMPT[:5] + u'\[\]' + PEXPECT_PROMPT[5:]
            ps2 = PEXPECT_CONTINUATION_PROMPT[:5] + u'\[\]' + PEXPECT_CONTINUATION_PROMPT[5:]
            prompt_change = u"PS1='{0}' PS2='{1}' PROMPT_COMMAND=''".format(ps1, ps2)
            shell = pexpect.replwrap.REPLWrapper(child, u'\$', prompt_change)
        return shell