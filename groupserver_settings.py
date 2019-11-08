"""
Settings for PyChat's Group Server application
Master commands:
    /updatesettings:
        Reload the settings from this file
    /masterhelp:
        Displays this help
    /destroy:
        Shuts down the server
"""

# Password for accessing master commands (always put immediately after the master command)
Master_password = "LetMeIn!"

# Message to show the user if they entered the wrong master password
Access_denied_message = "Access Denied!"

# Message to send to the user when they leave the server
Goodbye_message = "Goodbye"

# Message to send the user when they run the help command
Help_message = """
Commands:
    /nick:
        Sets your display name
    /leave:
        Leaves the group server
    /help:
        Displays this help
    /join:
        Joins the server without having to send any messages
    /usrlist:
        Displays the list of users on the server
"""

# Message to send the user when they join
Join_message = """
Welcome
Here's some help:
""" + Help_message

# Name of the auto user who sends messages to users
Host_username = "Server Host"

# The maximum file size of attachments (in MB)
Max_attachment_size = 2.5

# The filename to give the attachment if it exceeds the maximum size
Placeholder_attachment_filename = "Size exceeded limits.txt"

# What to make the attachment if it exceeds the maximum size
# The %(max)d is replaced with the maximum size (MB), and the %(size)d is replaced with the attachment size(MB)
Placeholder_attachment_text = """
Sorry, the attachment size exceeded the maximum attachment size of %(max)dMB. (Being %(size)dMB in size)
Please consider having the sender send this over email.
"""

# The number of users to keep track of before dolling out send errors
Message_backwash = 250

# The port for PyChat to use
Port = 1245

# The amount of time between when users can send messages (in seconds)
Time_between_messages = 0

# Whether to save users in a file if the server gets rebooted
Save_users_in_file = True