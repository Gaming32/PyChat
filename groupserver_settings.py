"""
Settings for PyChat's Group Server application
Master commands:
    !updatesettings:
        Reload the settings from this file
    !masterhelp:
        Displays this help
    !destroy:
        Shuts down the server (not working)
"""

# Password for modifying settings during runtime
Master_password = "LetMeIn!"

# Message to show the user if they entered the wrong master password
Access_denied_message = "Access Denied!"

# Message to send to the user when they leave the server
Goodbye_message = "Goodbye"

# Message to send the user when they run the help command
Help_message = """
Commands:
    !nick:
        Sets your display name
    !leave:
        Leaves the group server
    !help:
        Displays this help
    !join:
        Joins the server without having to send any messages
"""

# Message to send the user when they join
Join_message = """
Welcome
Here's some help:
""" + Help_message

# Name of the auto user who sends messages to users
Host_username = "Server Host"

# The port for PyChat to use
Port = 1245

# The amount of time between when users can send messages (in seconds)
Time_between_messages = 0

# Whether to save users in a file if the server gets rebooted (not working)
Save_users_in_file = True